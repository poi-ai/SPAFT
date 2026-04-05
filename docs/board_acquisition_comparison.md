# 板情報取得方式 比較・設計レポート

作成日: 2026-04-05

---

## 前提：認識の修正

> 「WebSocketのPUSHで受け取る処理は取引処理の一部でしかなく、独立した処理は存在しない」

**→ 修正が必要。独立スクリプトは存在する。**

```
src/board_record.py         ← REST ポーリング専用の独立スクリプト ✅
src/reception_websocket.py  ← WebSocket PUSH専用の独立スクリプト ✅（存在している）
src/main.py                 ← 取引処理（内部で api.info.board() を直接呼ぶが記録目的ではない）
```

ただし、両スクリプトが**保存するデータの種類が根本的に異なる**。

| スクリプト | 保存先テーブル | 保存内容 |
|---|---|---|
| `board_record.py` | `boards` or CSV | 板の10段気配値・現在株価・OVER/UNDER量 |
| `reception_websocket.py` | `ohlc` | 1分足の四本値（始値・高値・安値・終値・出来高） |

つまり「WebSocket で `boards` に相当するデータを記録する独立スクリプト」は存在しない。
取引処理内でも WebSocket で板情報を直接記録する処理はなく、`main.py` は REST API を都度叩いて板情報を取得しているだけ。

---

## 1. REST ポーリング方式（`board_record.py`）の詳細

### 仕組み

```
while True:
    for stock_code in target_code_list:
        GET /board/{stock_code}@1       # 銘柄ごとに1リクエスト
        time.sleep(0.1)                 # レート制限回避
    wait_time_next_second() or next_minute()
```

### 実装箇所

| 処理 | ファイル:行 |
|---|---|
| エントリーポイント | `src/board_record.py` |
| REST `/board` 呼び出し | `src/kabusapi/info.py:board()` |
| Service ラッパー | `src/service/collect/record.py:info_board()` |
| DB用フォーマット変換 | `src/util/mold.py:response_to_boards()` |
| CSV用フォーマット変換 | `src/util/mold.py:response_to_csv()` |
| DBへのINSERT | `src/db/board.py:insert()` |
| CSVへの追記 | `src/util/file_manager.py:write_csv()` |
| CSV後処理（指標計算） | `src/service/preprocess/board_mold.py:main()` |

### 取得タイミングと頻度

| `BOARD_RECORD_MODE` | 取得間隔 | 用途 |
|---|---|---|
| `1` | 1秒ごと | ほぼリアルタイムに近い記録 |
| `2` | 1分ごと | 標準的なML学習データ収集 |
| `3` | 1回のみ | デバッグ・スポット確認 |

### レート制限上の制約

銘柄情報系 API は **10件/秒**が上限。
コード中では銘柄間に `time.sleep(0.1)` を挿入しているため実質 **最大10銘柄/秒**。
例: 6銘柄 × 0.1秒 = 0.6秒の処理時間 → MODE=1（1秒ごと）は6銘柄程度が限界。
銘柄数が増えると1秒以内に取得しきれず、MODE=1でも実質1秒より遅くなる。

---

## 2. WebSocket PUSH方式（`reception_websocket.py`）の詳細

### 仕組み

```
# 初期化: 銘柄を登録
PUT /register → 銘柄をPUSH配信対象に追加

# 受信ループ（非同期）
ws.recv() → 約定・気配変動のたびにKabuStationがPUSHしてくる
  → operate_ohlc() で1分足OHLCに集計してメモリに保持
  → 分が変わったらDBにupsert
```

### 実装箇所

| 処理 | ファイル:行 |
|---|---|
| エントリーポイント | `src/reception_websocket.py` |
| 銘柄登録 | `src/kabusapi/register.py:register()` |
| WebSocket接続 | `src/kabusapi/websocket.py:connect()` |
| 受信ループ | `src/service/collect/record.py:websocket_main()` |
| OHLC集計処理 | `src/service/collect/record.py:operate_ohlc()` |
| OHLC用フォーマット変換 | `src/util/mold.py:response_to_ohlc()` |
| DBへのupsert | `src/db/ohlc.py:upsert()` |

### PUSH配信のタイミング

KabuStation は以下のタイミングでデータをプッシュしてくる:
- 約定が発生したとき
- 気配値が変動したとき（最良気配の変動）

**つまり約定・気配変動があるたびに即時送信される**。1分間に数十〜数百回届く銘柄もある。

### お昼休みの接続切断対応

CLAUDE.md にある通り、KabuStation は昼休み（11:30〜12:30）にWebSocket接続を切断する。
`reception_websocket.py` は前場・後場を分けて2回 `websocket_main()` を呼ぶことでこれに対応している:

```python
await self.service.collect.record.websocket_main(1)  # 前場（〜11:30で終了）
await self.service.collect.record.websocket_main(2)  # 後場（12:30〜）
```

---

## 3. 方式の比較

### データ特性の違い

| 観点 | REST ポーリング | WebSocket PUSH |
|---|---|---|
| **保存データ** | 板の10段気配値（全量） | 1分足OHLC（集計値） |
| **タイムスタンプ粒度** | 取得間隔次第（1秒/1分） | 約定・気配変動ごと（ミリ秒レベル） |
| **欠損リスク** | ポーリング間隔内の変動は失われる | 取引中の全変動を受け取れる |
| **1回分のデータ量** | 大（10段×買売×価格+数量＋各種指標） | 小（Symbol, CurrentPrice, TradingVolume 等） |

### システム特性の違い

| 観点 | REST ポーリング | WebSocket PUSH |
|---|---|---|
| **API呼び出し回数** | 銘柄数×取得頻度（レート制限に直撃） | 初回の登録のみ（受信は消費なし） |
| **遅延** | ポーリング間隔分のラグが必ずある | 数十〜数百ミリ秒（準リアルタイム） |
| **銘柄数の上限** | レート制限（10件/秒）が実質的な制約 | PUSH配信登録上限（50銘柄） |
| **実装の複雑さ** | シンプル（同期的なポーリングループ） | 非同期（asyncio）が必要 |
| **昼休みの対応** | 自動（wait_time で待機するだけ） | 明示的な再接続処理が必要 |
| **接続障害時** | 次のポーリングで自動復旧 | WebSocket再接続ロジックが必要 |

### 目的別の向き不向き

| 用途 | 向いている方式 | 理由 |
|---|---|---|
| ML学習用の板スナップショット収集 | **REST ポーリング** | 板の10段気配値（OVER/UNDER含む）が必要。WebSocket PUSHには含まれない情報がある |
| ML学習用の価格変動データ（OHLC）収集 | **WebSocket PUSH** | 全約定を拾えるため精度が高い。REST では粒度が粗くなる |
| スキャルピング取引の判断材料 | **REST ポーリング** | `scalping.py` の実装通り。必要なタイミングで最新板情報を取れれば十分 |
| リアルタイムアラート・監視 | **WebSocket PUSH** | 約定ごとに即時通知が必要な用途に適している |
| 多銘柄を同時に高頻度で取得 | **WebSocket PUSH** | REST は銘柄数×頻度でAPI上限に当たる |

### どちらが優れているか

**目的が「板の10段気配値の記録（ML学習用 boards テーブル）」ならREST ポーリング一択。**
WebSocket PUSH でもAPIレスポンスと同じキーのJSONが届くが、`boards` テーブルに保存するための処理（`response_to_boards()` + `insert_board()`）は `reception_websocket.py` には実装されていない。

**目的が「価格の動きのOHLC記録」ならWebSocket PUSH が明確に優れている。**
REST ポーリングの1分足では分内の全動きを取れないが、WebSocket は全約定を受け取れるため精度が高い。

---

## 4. 「WebSocket PUSH で boards テーブルに記録する独立スクリプト」を作るには

現状 `reception_websocket.py` は boards テーブルへの記録には対応していない。
WebSocket で受け取ったデータを `boards` テーブルに記録する独立スクリプトを追加するとした場合の設計を示す。

### 前提：WebSocket PUSH のデータと boards テーブルの関係

KabuStation の WebSocket PUSH は REST `/board` とほぼ同一のJSONフォーマットでデータを送信する。
`response_to_boards()` は REST レスポンスを boards テーブル用に変換するが、**PUSHデータにも同じキーが含まれるためそのまま流用できる**。

ただし `get_time`（取得日時）キーは PUSH データに含まれないため、受信時刻を手動で付与する必要がある（`board_record.py:67` と同じ処理）。

### 流用できる既存実装

| 処理 | 流用元 | 変更要否 |
|---|---|---|
| 初期処理（営業日判定・全銘柄登録解除・銘柄登録） | `record.record_init(push_mode=True)` | 変更不要 |
| WebSocket接続 | `kabusapi/websocket.py:connect()` | 変更不要 |
| 受信ループのフレーム | `record.websocket_main()` | コールバック部分のみ変更 |
| boards用フォーマット変換 | `util/mold.py:response_to_boards()` | 変更不要 |
| boards テーブルINSERT | `db/board.py:insert()` | 変更不要 |
| 時刻チェック・前場/後場分割 | `reception_websocket.py` のパターン | 変更不要 |

### 必要な変更・追加の範囲

#### (1) `record.py` に新しいコールバックメソッドを追加

`operate_ohlc()` と並行して、受信データを boards テーブルに記録する非同期メソッド `operate_board()` を追加する。

```python
# src/service/collect/record.py に追加するイメージ（実装ではなく設計メモ）
async def operate_board(self, reception_data):
    # 取得時刻を付与（board_record.py と同様）
    reception_data['get_time'] = datetime.now(timezone(timedelta(hours=9)))

    # boards テーブル用フォーマットに変換（既存メソッドを流用）
    board_table_dict = self.util.mold.response_to_boards(reception_data)
    if board_table_dict == False:
        return False

    # boards テーブルに INSERT（既存メソッドを流用）
    self.insert_board(board_table_dict)
    return True
```

#### (2) `websocket_main()` のコールバック切り替え

現在 `websocket_main()` のコールバックは `operate_ohlc()` 固定:

```python
# 現在の実装（record.py:147）
asyncio.create_task(self.operate_ohlc(json.loads(message)))
```

`mode` パラメータを追加してコールバックを切り替えられるようにする、またはコールバック関数を引数で渡す設計にする。

```python
# 設計案A: mode パラメータ追加
async def websocket_main(self, time_period, mode = 'ohlc'):
    # mode == 'ohlc' → operate_ohlc()
    # mode == 'board' → operate_board()

# 設計案B: コールバック関数を引数で受け取る（より疎結合）
async def websocket_main(self, time_period, callback = None):
    # callback is None → operate_ohlc()（後方互換）
    # callback = self.operate_board → boards記録
```

設計案Bの方が `websocket_main()` の責務を「受信ループの管理」に限定できるため拡張性が高い。

#### (3) 新しいエントリースクリプトを追加

`reception_websocket.py` を参考に、boards記録専用の起動ファイルを追加する。

```
src/board_record_ws.py    ← 新規追加するイメージ（既存 reception_websocket.py と対になる）
```

既存 `board_record.py` と `reception_websocket.py` の構造を組み合わせたものになる:
- `board_record.py` から: DB初期化あり（`use_db=True`）、`BOARD_RECORD_*` 設定の読み込み
- `reception_websocket.py` から: `asyncio.run()`、前場/後場の2段階呼び出し

### 構成まとめ

```
【新規追加が必要なもの】
  src/board_record_ws.py           ← エントリースクリプト（新規）
  src/service/collect/record.py    ← operate_board() 追加 + websocket_main() にコールバック引数追加

【変更不要・そのまま流用できるもの】
  src/kabusapi/websocket.py        ← WebSocket接続
  src/kabusapi/register.py         ← 銘柄登録
  src/service/collect/record.py    ← record_init(), unregister_all(), insert_board()
  src/util/mold.py                 ← response_to_boards()
  src/db/board.py                  ← insert()
  src/base.py                      ← 初期化チェーン（use_db=True で起動）
```

### 既存 `board_record.py`（REST方式）と新 `board_record_ws.py`（WebSocket方式）の住み分け

| 観点 | `board_record.py`（REST） | `board_record_ws.py`（WebSocket）|
|---|---|---|
| 保存先 | `boards` テーブル or CSV | `boards` テーブル |
| 板データの時間粒度 | 1秒/1分（設定次第） | 気配変動ごと（準リアルタイム） |
| 多銘柄への対応 | 銘柄数が増えるほど遅延増 | 最大50銘柄まで等遅延 |
| ML学習データとしての価値 | 低頻度・確実な間隔 | 高頻度・気配変動ベース |
| 実装難易度 | 低（同期処理） | 中（非同期・再接続対応必要） |

**基本的には REST ポーリングで足りる。** 1秒ごとに板情報を記録したい、かつ銘柄数が多い、というケースで初めてWebSocket方式の利点が出てくる。

---

## 5. 既存コードの問題点（WebSocket方式に影響するもの）

`reception_websocket.py:17` に潜在的なバグがある:

```python
record_init = self.service.collect.record.record_init(config.RECORD_STOCK_CODE_LIST, config.BOARD_RECORD_DEBUG, push_mode = True)
if record_init == False:
    return False
```

`record_init()` の戻り値は `(bool, list)` のタプルだが、タプルそのものを `False` と比較している。
タプルは空でない限り常に truthy なので、`record_init` が `(False, None)`（非営業日）を返しても
`if record_init == False:` は **False** と評価され、そのまま処理が続いてしまう。

正しくは:
```python
result, target_code_list = self.service.collect.record.record_init(...)
if result == False:
    return False
```

新しい WebSocket ベースのスクリプトを実装する際はこのバグを踏まないように注意が必要。
