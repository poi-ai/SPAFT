# SPAFT 開発優先度計画

作成日: 2026-04-04

## 方針

取引アルゴリズム（スキャルピング・ML注文・テクニカル注文）は現在**凍結中**。
アルゴリズム自体の精度が出ておらず、動かすほど損失が出る状態のため、取引ロジックには触れない。

**対応順序:**
1. 板情報の取得・記録（基盤）を固める
2. MLパイプライン（学習データの整備・モデル精度改善）
3. 取引ロジック（凍結解除後に対応）

---

## システム構成と現状

### 処理の区分

| 区分 | 主ファイル | 状態 |
|---|---|---|
| 板情報取得・記録 | `board_record.py`, `reception_websocket.py`, `service/record.py` | ✅ 概ね動作 |
| ML学習パイプライン | `analytics/catboost_clf.py`, `analytics/catboost_reg.py` | ⚠️ データリーク疑い |
| 取引実行（凍結） | `main.py`, `service/trade.py` | 🔒 凍結中 |
| GUI（凍結） | `gui.py` | 🔒 凍結中 |

### 板情報取得の2ルート

```
board_record.py         → APIポーリング（1秒/1分/1回）→ DB or CSV
reception_websocket.py  → WebSocket PUSH配信       → 四本値DB or 最良気配CSV
```

### 動作不可なファイル

| ファイル | 原因 |
|---|---|
| `src/data_search.py` | `from db_base import Db_Base` など旧クラスのimport |
| `src/listed_update.py` | 同上 |

---

## Phase 1 — 板情報基盤の整備（優先対応）

### 1. #33 エラー行数出力の統一（最初に対応）

**理由**: 以降の作業でバグを踏んだ際の調査コストを下げるため、最初に対応する。

- `error_output(message, e, traceback.format_exc())`を使っていないtry-exceptブロックを探して統一
- 対象: `src/service/record.py`（板情報記録の中核）、`src/kabusapi/websocket.py` 等
- `src/base.py`の`error_output()`はすでに`traceback.format_exc()`を受け取れる設計

### 2. #31 最良気配値CSV記録のマージ（実装中）

**理由**: WebSocket PUSH配信で最良気配・出来高をCSVに記録する機能。ML学習データの収集基盤になる。

`origin/#31`ブランチの変更内容:
- `config.py.sample` に `WEBSOCKET_MODE` 追加（1=四本値DB, 2=最良気配CSV）
- `reception_websocket.py`: `WEBSOCKET_MODE`でDB接続の有無を制御
- `service/record.py`: `record_board_price()`メソッド追加（CSV出力先: `csv/result/kehai.csv`）
- `kabusapi/register.py`: ドキュメント修正のみ

**確認事項（マージ前）:**
- `record.py`の`record_board_price()`内: `datetime.now()`と`import datetime`の記述が一致しているか確認
- `record.py` 321行目付近: `self.info_board(self, stock_code, ...)` のように`self`が2重渡しになっていないか確認

### 3. `data_search.py` / `listed_update.py` の修正

**理由**: 板情報の検索・上場銘柄マスターの更新に必要なスクリプト。現在`import`でエラーになる。

修正内容（各ファイル同じパターン）:
```python
# 修正前（旧アーキテクチャ）
from db_base import Db_Base
from db_operate import Db_Operate

# 修正後（現行アーキテクチャ）
from base import Base  # Base継承でService/DB/API全てを初期化
```
ロジック自体は完成しているため、importとクラス継承の書き換えのみで動作する見込み。

### 4. #29 クローズ（コード変更なし）

- コミット`40f2251`で対応済み
- GitHubでIssueをクローズ、ローカルの`#29`ブランチを削除するだけ

---

## Phase 2 — データパイプライン強化

### 5. #32 日足データスクレイピング

※ `origin/#32`ブランチは現時点で存在しない。新規に作成して実装する。

- Yahoo!Financeから日足OHLCデータを取得するスタンドアロンスクリプト
- 既存の`src/service/past_record.py`・`src/service/mold_past_record.py`の役割と重複しないか確認してから設計
- 保存先: `csv/past_ohlc/`以下（既存の学習データと同形式）

### 6. #20 板情報CSVへの指標カラム追加

- `src/service/board_mold.py`に指標計算を追加（`service/__init__.py`経由で呼ばれる）
- `src/util/indicator.py`（約960行）に既存の指標計算があるため最大限再利用
- #31でCSV記録が整備された後に対応

### 7. #28 注文可能価格の事前計算とリスト化

- `src/util/stock_price.py`にユーティリティメソッドを追加
- ストップ高〜ストップ安の全注文可能価格をリストで返す関数を実装
- 板情報成形時の価格チェックに使える

### 8. #11 NTPサーバーへのアクセス量削減

- `src/util/culc_time.py`の`get_now()`をキャッシュ化（N秒に1回だけNTP取得、それ以外は`datetime.now()`）
- `board_record.py`のメインループで毎回呼ばれているため

---

## Phase 3 — MLパイプライン整備

### 9. #30 データリーク調査とモデル再学習

**現状:**
- `src/analytics/catboost_clf.py`では`leak_columns`による除外対応済み
- ただし時系列データの訓練/テスト分割が無作為になっていないか未検証

**調査手順:**
1. 現モデルの精度指標を記録（ベースライン）
2. 訓練データとテストデータの日付を確認（同一日付が両方に混在していないか）
3. 時系列分割（直近N日をテストに固定）に修正
4. 再学習して精度が合理的な範囲（55〜65%程度）に収まるか確認

Phase 2でデータパイプライン（#31, #32, #20）が整備されてから最新データで実施。

---

## 凍結中（現時点では対応しない）

| Issue | 内容 | 解除条件 |
|---|---|---|
| #14 | 損切りバグ調査・修正 | 取引凍結解除後 |
| #18 | GUI注文機能追加 | 取引凍結解除後 |
| #27 | GUIでスキャルピング設定 | 取引凍結解除後 |
| #8 | すり抜け注文のエラー非扱い | 取引凍結解除後 |
| #4 | 取引記録のDBレコード化 | 取引凍結解除後 |

---

## フェーズまとめ

| Phase | Issues | 主目的 |
|---|---|---|
| Phase 1 | #33, #31マージ, broken files修正, #29クローズ | 板情報基盤の整備 |
| Phase 2 | #32, #20, #28, #11 | データパイプライン強化 |
| Phase 3 | #30 | MLパイプライン整備 |
| 凍結 | #14, #18, #27, #8, #4 | 取引凍結解除後に対応 |

---

## 最初の具体的アクション

```bash
# 1. devから作業ブランチを作成
git checkout dev
git checkout -b '#33'

# 2. service/record.py 等のtry-exceptにtraceback出力を統一
# 3. PR: #33 → test

# 次: #31ブランチのコードレビュー → マージPR
# 次: data_search.py / listed_update.py のimport修正
```

---

## 検証方法

- **#31マージ後**: `python reception_websocket.py`を実行し、`csv/result/kehai.csv`にデータが書き込まれることを確認
- **data_search.py修正後**: `cd src && python data_search.py`がエラーなく起動することを確認
- **#30**: `src/analytics/catboost_clf.py`を実行して精度指標を記録し、合理的な範囲内か確認
