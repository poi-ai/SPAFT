# SPAFT — Claude Code コンテキスト

## プロジェクト概要

**SPAFT (Scalping Profit Algorithm From TSE)**
auカブコム証券のKabuStation APIを利用した東京証券取引所(TSE)向け自動スキャルピングシステム。
Fintech または Premium プランが必須。
デイトレ信用注文でのイントラデイポジション管理、損益確定、板情報収集、MLモデルによる価格予測を行う。

## プラットフォーム制約

**Windowsのみ動作する。** KabuStation（kabuステーション）デスクトップアプリがWindows専用のため。
Linuxへの移植、Dockerコンテナ化、クロスプラットフォーム対応は提案しないこと。

## 実行コマンド

スクリプトはすべて **`src/` ディレクトリ内で実行する**こと（bare importのため `import config` 等が解決できる）。

```bash
cd src
python main.py              # スキャルピングメイン処理
python gui.py               # GUI注文ツール
python board_record.py      # 板情報記録
python yutai.py [証券コード] [株数] [信用種別]  # 信用返済成行注文
```

ML学習スクリプトはcsvを生成したリポジトリルートから実行する:
```bash
python src/analytics/catboost_clf.py
python src/analytics/catboost_reg.py
```

## config.py の扱い

- `src/config.py` は `.gitignore` 対象 — **絶対にコミットしない**
- テンプレートは `src/config.py.sample`
- 設定値を参照するコードは必ず `import config` してから `config.XXXX` でアクセスする
- コード内にパスワード・トークンをハードコードしてはいけない
- `config.py.sample` への追加は日本語コメント必須

## アーキテクチャ — 呼び出し方向の制約

```
Controller (src/main.py, gui.py, board_record.py, yutai.py)
    ↓ 継承
Base (src/base.py)
    ↓ インスタンス生成
Service (src/service/__init__.py)
    ↓ 使用
├── KabusApi (src/kabusapi/__init__.py)
├── Db       (src/db/__init__.py)
└── Util     (src/util/__init__.py)
```

**許可される呼び出し方向（src/service_base.py Memo参照）:**
- Controller → Service, Util  ✅
- Service → Util, KabusApi, Db  ✅

**禁止:**
- Controller → KabusApi 直接呼び出し  ❌
- Controller → Db 直接呼び出し  ❌
- KabusApi → Db  ❌
- Db → Util  ❌（必要性が生じれば要検討）

この制約に違反すると `Base.__init__` の初期化チェーンが崩れる。

### 新規クラスの登録手順

**Serviceクラス追加時:**
1. `src/service/<snake_case>.py` を作成（`ServiceBase` を継承）
2. `src/service/__init__.py` に import と `Service.__init__()` 内でのインスタンス生成を追加

**KabusApiクラス追加時:**
1. `src/kabusapi/<snake_case>.py` を作成
2. `src/kabusapi/__init__.py` に import と `KabusApi.service_init()` 内でのインスタンス生成を追加

**Dbクラス追加時:**
1. `src/db/<snake_case>.py` を作成
2. `src/db/__init__.py` に import と `Db.service_init()` 内でのインスタンス生成を追加

## KabuStation API

### エンドポイント

| 環境 | REST | WebSocket |
|---|---|---|
| 本番（`config.API_PRODUCTION = True`） | `http://localhost:18080/kabusapi` | `ws://localhost:18080/kabusapi` |
| 検証（`config.API_PRODUCTION = False`） | `http://localhost:18081/kabusapi` | `ws://localhost:18081/kabusapi` |

### 認証

1. 起動時に `POST /token` で `{"APIPassword": "<password>"}` を送信してトークンを取得
2. 以降のリクエストはヘッダー `X-API-KEY: <token>` を付与
3. KabuStation が再起動した場合はトークンが無効化される → `exit()` して全体を再起動が必要
4. 自動再接続はトークン再取得まで行わない

### レート制限（TIPS.md より）

| カテゴリ | 上限 |
|---|---|
| 発注系（/sendorder 等） | **5件/秒** |
| 余力情報系（/wallet 等） | **10件/秒** |
| 銘柄情報系（/symbol, /board 等） | **10件/秒** |
| 登録系（/register 等） | 記載なし |

連続してAPIを呼ぶ初期化フローでは `time.sleep(1)` を挿入すること。

### WebSocket PUSH

- エンドポイント: `ws://localhost:18080/kabusapi/websocket`
- リアルタイム板情報の受信に使用
- **昼休み（11:30〜12:30 JST）にKabuStationがWebSocket接続を切断する**
  - 対応: 11:30前にWebSocketを切断し、12:29:59に再接続する（前場/後場の判定が重要）
- 購読登録前に必ず `PUT /unregister/all` で既存登録を解除すること
  - 未解除のまま追加すると50銘柄上限超えでエラーになる

## 市場時間（JST / UTC+9）

時刻は NTPサーバーから取得（`src/util/culc_time.py:CulcTime.get_now()`）。
NTPサーバーのフォールバック順: `ntp.jst.mfeed.ad.jp` → `time.cloudflare.com` → `time.aws.com`

### `exchange_time()` の戻り値

| 戻り値 | 意味 | 時間帯 |
|---|---|---|
| `1` | 前場取引時間 | 09:00〜11:30 |
| `2` | 後場取引時間 | 12:30〜15:25 |
| `3` | 取引時間外（寄り付き前） | 〜09:00 |
| `4` | 取引時間外（お昼休み） | 11:30〜12:30 |
| `5` | 取引時間外（大引け後） | 15:30〜 |
| `6` | クロージング・オークション | 15:25〜15:30 |

取引所の休場日: 土日、祝日、12/31、1/1〜1/3
祝日リストは `src/util/culc_time.py:get_holiday_list()` に2030年まで硬書き。
2031年以降は外部API `https://holidays-jp.github.io/api/v1/date.json` を使用（`holidays_jp_api()`）。
※ 2030年になったら `get_holiday_list()` の `until_year` と祝日データを追加すること

## 呼値（Yobine）ルール

東証の株価は連続した値を動かない。最小変動幅（呼値）は株価と呼値グループによって決まる。
**価格計算には必ず `src/util/stock_price.py:StockPrice` のメソッドを使うこと。**
`price + 1` や `price - 1` は誤り（銘柄・価格帯によって呼値が1円ではない）。

呼値グループ（yobine_group）は `/symbol/{証券コード}` エンドポイントから取得。

**最も一般的な呼値グループ 10000 のルール（`get_price_range()` より）:**

| 株価 | 呼値 |
|---|---|
| 3,000円未満 | 1円 |
| 3,000〜5,000円 | 5円 |
| 5,000〜30,000円 | 10円 |
| 30,000〜50,000円 | 50円 |
| 50,000〜300,000円 | 100円 |
| 300,000〜500,000円 | 500円 |
| 500,000〜3,000,000円 | 1,000円 |

`config.py` の `ORDER_LINE`, `SECURING_BENEFIT_BORDER`, `LOSS_CUT_BORDER`, `TRAIL` は **pip数（= 呼値の倍数）** であり、円単位ではない。

## 日本株式用語集

| 日本語 | 読み | 意味 |
|---|---|---|
| 前場 | ぜんば | 午前の取引時間（09:00〜11:30） |
| 後場 | ごば | 午後の取引時間（12:30〜15:30） |
| お昼休み | おひるやすみ | 取引中断時間（11:30〜12:30） |
| 板 | いた | 注文板（Order Book） |
| 呼値 | よびね | 最小価格変動幅（Tick Size） |
| 信用取引 | しんようとりひき | 証券会社からの借入による取引（Margin Trading） |
| デイトレ信用 | | 当日中に返済する信用取引（カブコムAPI経由は手数料0円） |
| 制度信用 | せいどしんよう | 決められたルールによる信用取引 |
| 一般信用 | いっぱんしんよう | 証券会社独自ルールによる信用取引 |
| 余力 | よりき | 発注可能残高 |
| 約定 | やくじょう | 注文が成立すること（Fill / Execution） |
| 成行 | なりゆき | 市場価格での注文（Market Order） |
| 指値 | さしね | 指定価格での注文（Limit Order） |
| 証券コード | しょうけんコード | 銘柄識別番号（4桁: 東証等） |
| 銘柄 | めいがら | 個別株式 |
| 四本値 | しほんね | OHLC（始値・高値・安値・終値） |
| ストップ高/安 | | 値幅制限上限/下限（Daily Limit Up/Down） |
| 値幅上限/下限 | ねはばじょうげん | その日の注文可能価格の上限/下限 |
| 気配 | けはい | 気配値（Quote） |
| 特別気配 | とくべつけはい | 需給不均衡時の特別気配値 |
| 優待 | ゆうたい | 株主優待（Shareholder Benefits Program） |
| 権利落ち日 | けんりおちび | 優待権利の基準日翌営業日（株価下落が起きやすい） |
| 引け | ひけ | 取引終了 |
| 大引け | おおひけ | 後場の取引終了 |
| 寄り付き | よりつき | 前場の取引開始 |

## データベーススキーマ概要

MySQL 8.0、DB名: `spaft`

| テーブル | 目的 |
|---|---|
| `boards` | リアルタイム板情報スナップショット（ML学習データ） |
| `orders` | 注文レコード（ステータス追跡） |
| `holds` | 保有ポジション |
| `buying_power` | 余力スナップショット |
| `ohlc` | 四本値データ |
| `listed` | 上場銘柄マスタ |
| `errors` | エラーログ |
| `api_process` | API呼び出し監査ログ |

**主要コード値:**

| カラム | 値 | 意味 |
|---|---|---|
| `market_code` | 1 | 東証（TSE） |
| `market_code` | 3 | 名証 |
| `market_code` | 5 | 福証 |
| `market_code` | 6 | 札証 |
| `buy_sell` | 1 | 売 |
| `buy_sell` | 2 | 買 |
| `cash_margin` | 1 | 現物買 |
| `cash_margin` | 2 | 現物売 |
| `cash_margin` | 3 | 信用新規 |
| `cash_margin` | 4 | 信用返済 |

## コーディング規約

- **コメント・ログメッセージは日本語で書く**（既存コード全体が日本語）
- メソッドの戻り値は `(bool, value_or_error)` タプルが標準
  - 成功: `(True, 結果値)`
  - 失敗: `(False, エラーメッセージ or エラーコード)`
- エラー処理: `self.error_output(message, e, traceback.format_exc())` を使う
  - 自動でログ出力 + LINE Notify 通知（トークンが設定されている場合）
- ログ出力: `self.log.info()`, `self.log.error()`, `self.log.warning()`
  - ログファイルは `log/YYYYMMDD.log` に出力
- 新規 Service クラスは `ServiceBase` を継承し、コンストラクタで `api_headers, api_url, ws_url, conn` を受け取る
- API / DB が不要なServiceは `super().__init__(False, False, False, False)` で初期化

## ML / Analytics

`src/analytics/` 内のスクリプトはスタンドアロンの学習スクリプトで、トレードエンジンからはインポートされない。
学習データ: `csv/past_ohlc/formatted/formatted_ohlc_YYYYMMDD.csv`（rows 30〜-25でスライス）
学習済みモデル: `model/` ディレクトリに `.cbm` 形式（CatBoost Binary）で保存
予測ターゲット: `change_3min_flag`（3分後に株価が上昇するか否かの2値分類）

## 現在動作しないファイル（修正依頼が来ても手を加えないこと）

| ファイル | 理由 |
|---|---|
| `src/data_search.py` | 新ディレクトリ構成に未対応（フロー自体は完成） |
| `src/listed_update.py` | 新ディレクトリ構成に未対応（フロー自体は完成） |
