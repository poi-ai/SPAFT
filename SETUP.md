# SPAFT セットアップ手順書

新しいPCにSPAFTを導入する際の手順をまとめた手順書です。
セットアップ後は `src/setup_check.py` を実行して正しく設定できているか確認してください。

---

## 1. 前提条件

- **OS**: Windows 10 / 11（KabuStationはWindows専用）
- **Python**: 3.9 以上
- **MySQL**: 8.0 以上
- **KabuStation（かぶステーション）**: auカブコム証券のデスクトップアプリ（Fintech または Premium プラン必須）

---

## 2. リポジトリのクローン

```bash
git clone https://github.com/poi-ai/SPAFT.git
cd SPAFT
```

---

## 3. Pythonモジュールのインストール

```bash
pip install -r requirements.txt
```

### インストールされるモジュール

| モジュール | 用途 |
|---|---|
| pymysql | MySQL接続 |
| requests | KabuStation REST API呼び出し |
| ntplib | NTPサーバーからの正確な時刻取得 |
| catboost | 機械学習モデル（CatBoost） |
| scikit-learn | 機械学習ユーティリティ |
| pandas | データ処理 |
| numpy | 数値計算 |
| tkcalendar | GUIカレンダーウィジェット |

---

## 4. MySQLのセットアップ

### 4-1. MySQLのインストール

[MySQL公式サイト](https://dev.mysql.com/downloads/mysql/)からMySQL 8.0をダウンロードしてインストールする。

### 4-2. データベースの作成

MySQLに接続してデータベースを作成する。

```sql
mysql -u root -p
```

```sql
source sql/db/spaft.sql
```

または直接実行:

```sql
CREATE DATABASE spaft;
```

### 4-3. テーブルの作成

SPAFTルートディレクトリ内の `sql/ddl/` に各テーブルのDDLが格納されている。
MySQLに接続後、以下を実行してすべてのテーブルを作成する。

```sql
USE spaft;
source sql/ddl/api_process.sql
source sql/ddl/board.sql
source sql/ddl/buying_power.sql
source sql/ddl/errors.sql
source sql/ddl/holds.sql
source sql/ddl/listed.sql
source sql/ddl/ohlc.sql
source sql/ddl/orders.sql
```

---

## 5. configファイルの設定

### 5-1. サンプルファイルのコピー

```bash
copy src\config.py.sample src\config.py
```

### 5-2. 各パラメータの設定

`src/config.py` をテキストエディタで開き、以下の項目を設定する。

#### DB接続情報

| パラメータ | 説明 | 例 |
|---|---|---|
| `DB_HOST` | MySQLのホスト名 | `'localhost'` |
| `DB_USER` | MySQLのユーザー名 | `'root'` |
| `DB_PASSWORD` | MySQLのパスワード | `'your_password'` |
| `DB_NAME` | データベース名 | `'spaft'`（変更不要） |

#### KabuStation API設定

| パラメータ | 説明 |
|---|---|
| `API_PASSWORD` | KabuStationアプリ > 設定 > API で設定したパスワード（取引パスワードとは別） |
| `TRADE_PASSWORD` | 取引用パスワード |
| `API_PRODUCTION` | `True`（本番環境）/ `False`（検証環境） |

#### その他（任意）

| パラメータ | 説明 |
|---|---|
| `LINE_MESSAGING_API_TOKEN` | LINEへのエラー通知用トークン（設定しなくても動作する） |

---

## 6. KabuStationの設定

1. auカブコム証券のマイページからKabuStationをダウンロード・インストール
2. KabuStationを起動してログイン
3. メニュー > 設定 > API からAPIを有効化し、パスワードを設定する
4. `config.py` の `API_PASSWORD` に手順3で設定したパスワードを入力する

> **注意**: APIパスワードは取引パスワードとは異なります。

---

## 7. セットアップ確認

すべての設定が完了したら、以下のコマンドでチェックスクリプトを実行する。
スクリプトは必ず `src/` ディレクトリ内で実行すること。

```bash
cd src
python setup_check.py
```

各項目が `[OK]` になっていれば正常にセットアップできている。

---

## 8. 実行方法

セットアップ完了後の各スクリプトの実行方法は `README.md` を参照。
