# SPAFT

**Scalping Profit Algorithm From TSE**
auカブコム証券のKabuStation APIを使った東京証券取引所（TSE）向け自動スキャルピングシステム。

---

## 概要

低額資金からリスクを最大限に抑えたイントラデイスキャルピングを実現するシステムです。
Npipsスキャルピング（指定pip数での買い・利確・損切り・トレール）を自動実行し、板情報の収集・機械学習による価格予測も行います。

---

## 必要環境

### ハードウェア・OS
- **Windows 11**（KabuStation APIはWindowsのみで動作）

### アカウント
- auカブコム証券 **Fintechプラン** または **Premiumプラン**
- KabuStation（kabuステーション）アプリのインストール・ログイン・API設定が完了していること

### ソフトウェア
| ソフトウェア | バージョン |
|---|---|
| Python | 3.12 |
| MySQL | 8.0 |
| KabuStation | 最新版 |

---

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/poi-ai/SPAFT.git
cd SPAFT
```

### 2. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 3. データベースの作成

```bash
mysql -u root -p -e "CREATE DATABASE spaft DEFAULT CHARSET utf8mb4;"
```

`sql/ddl/` 内のSQLファイルを順番に実行してテーブルを作成します。

```bash
mysql -u root -p spaft < sql/ddl/boards.sql
mysql -u root -p spaft < sql/ddl/orders.sql
# ... 他のDDLファイルも同様に実行
```

### 4. 設定ファイルの作成

```bash
cp src/config.py.sample src/config.py
```

`src/config.py` を編集して各種設定を入力します（次のセクション参照）。

---

## 設定

`src/config.py` の主要パラメータ:

| パラメータ | 説明 |
|---|---|
| `API_PASSWORD` | KabuStation で設定した API パスワード |
| `TRADE_PASSWORD` | 取引パスワード |
| `API_PRODUCTION` | `True`: 本番環境、`False`: 検証環境（推奨: 最初は `False` で動作確認） |
| `DB_HOST` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | MySQL 接続情報 |
| `STOCK_CODE` | スキャルピング対象銘柄の証券コード |
| `ORDER_LINE` | 現在値の何pip下に買い注文を入れるか |
| `SECURING_BENEFIT_BORDER` | 利確するpips数 |
| `LOSS_CUT_BORDER` | 損切りするpips数 |
| `TRAIL` | トレール幅（pip数） |
| `LINE_TOKEN` | LINE Notify APIトークン（任意・エラー通知に使用） |

> **pip = 1呼値（最小価格変動単位）** です。1円ではありません（銘柄・価格帯で異なります）。

---

## 使い方

すべてのスクリプトは **`src/` ディレクトリ内で実行** してください。

```bash
cd src
```

### スキャルピング自動取引

```bash
python main.py
```

市場時間内に自動でスキャルピングを実行します。
`config.RECOVERY_SETTLEMENT = True` に設定すると、保有ポジションの強制成行決済のみ行います。

### GUI注文ツール

```bash
python gui.py
```

KabuStation API経由での手動注文をGUI操作で行います。
誤発注防止のため、日本株以外・一般口座・法人口座などには制限がかかっています。

### 板情報記録

```bash
python board_record.py
```

`config.RECORD_STOCK_CODE_LIST` で指定した銘柄の板情報をリアルタイムで記録します（DBまたはCSVに出力）。

### 優待権利落ち成行決済

```bash
python yutai.py [証券コード] [株数] [信用種別]
```

| 引数 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| 証券コード | ✅ | - | 対象銘柄の4桁コード |
| 株数 | - | 100 | 決済する株数 |
| 信用種別 | - | 2（一般） | 1: 制度信用、2: 一般信用 |

---

## ディレクトリ構成

```
SPAFT/
├── src/
│   ├── analytics/          # CatBoostによる機械学習（学習・予測スクリプト）
│   ├── db/                 # データベース操作クラス
│   ├── kabusapi/           # KabuStation APIラッパークラス
│   ├── service/            # ビジネスロジック（取引・記録・シミュレーション等）
│   ├── util/               # 共通ユーティリティ（時間計算・呼値計算・ログ等）
│   ├── base.py             # Controllerクラスの基底クラス
│   ├── service_base.py     # Serviceクラスの基底クラス
│   ├── main.py             # スキャルピングメイン処理
│   ├── gui.py              # GUI注文ツール
│   ├── board_record.py     # 板情報記録
│   └── yutai.py            # 優待権利落ち成行決済CLI
├── sql/ddl/                # テーブル定義（DDL）
├── csv/                    # データ出力先
├── model/                  # 学習済みCatBoostモデル（.cbm）
├── log/                    # ログファイル（日付別）
├── config.py.sample        # 設定ファイルのテンプレート
├── TIPS.md                 # 手数料・APIレート制限等の参考情報
└── CLAUDE.md               # Claude Code向けプロジェクトコンテキスト
```

---

## 機能一覧

### 実装済み

**自動取引**
- 指定pips数での買い注文・利確・損切り・トレール（Npipsスキャルピング）
- 強制成行決済モード
- 前場・後場・昼休みの時間帯管理
- WebSocket切断時の自動再接続（昼休み対応）

**板情報収集**
- リアルタイム板情報のDB/CSV記録（秒次・分次・1回モード）
- 複数銘柄の同時記録

**機械学習**
- CatBoostによる3分後株価変動の予測（分類・回帰）
- ベイズ最適化によるハイパーパラメータチューニング

**その他**
- LINE Notifyによるエラー通知
- NTPサーバーを使った正確な時刻同期
- 取引シミュレーション（DB保存済み板データによるバックテスト）

---

## 使用API

- [kabuステーション®API](https://github.com/kabucom/kabusapi) — 注文・板情報・余力取得等
- [Holidays JP API](https://holidays-jp.github.io/) — 祝日判定（2030年以降）
- LINE Notify API — エラー通知（任意）
