# 新規DBテーブルの追加

引数で指定されたテーブル名のDBテーブルと対応するPythonクラスを作成し、必要な場所に登録する。

テーブル名: $ARGUMENTS

---

## 手順

### 1. 既存のDDLファイルを参照してスタイルを確認する

`sql/ddl/` ディレクトリの既存ファイルをひとつ読んでスタイルを把握すること。

### 2. `sql/ddl/<table_name>.sql` を作成

以下の規約に従うこと:
- エンジン: `ENGINE=InnoDB`
- 文字コード: `DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci`
- 全カラムに日本語の `COMMENT` を付ける
- 必須カラム:
  - `id INT NOT NULL AUTO_INCREMENT COMMENT 'ID'` (PRIMARY KEY)
  - `created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '作成日時'`

テンプレート:
```sql
CREATE TABLE IF NOT EXISTS `<table_name>` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'ID',
  -- <ここにカラムを追加>
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '作成日時',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='<テーブルの目的を日本語で>';
```

### 3. `src/db/<table_name>.py` を作成

以下のテンプレートに従うこと:

```python
import traceback

class <ClassName>():
    '''<テーブルの目的を日本語で説明>'''

    def __init__(self, log, conn, dict_return):
        '''
        初期設定処理

        Args:
            log(Log): ログクラスのインスタンス
            conn(pymysql.Conn): MySQLへの接続情報
            dict_return(DictCursor): SELECT結果をdict型で返すカーソル

        '''
        self.log = log
        self.conn = conn
        self.dict_return = dict_return

    def insert(self, <params>):
        '''
        <テーブル名>テーブルへのINSERT

        Args:
            <param>(型): <説明>

        Returns:
            result(bool): 実行結果
            error_message(str): エラーメッセージ（失敗時）
        '''
        try:
            with self.conn.cursor() as cursor:
                sql = """
                    INSERT INTO <table_name> (<columns>)
                    VALUES (<values>)
                """
                cursor.execute(sql, (<bindings>,))

        except Exception as e:
            self.log.error(f'<テーブル名>のINSERTでエラー\n{e}\n{traceback.format_exc()}')
            return False, str(e)

        return True, None

    def select(self, <params>):
        '''
        <テーブル名>テーブルからのSELECT

        Args:
            <param>(型): <説明>

        Returns:
            result(bool): 実行結果
            rows(list[dict]) or error_message(str): 取得結果 or エラーメッセージ
        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = """
                    SELECT * FROM <table_name>
                    WHERE <condition>
                """
                cursor.execute(sql, (<bindings>,))
                rows = cursor.fetchall()

        except Exception as e:
            self.log.error(f'<テーブル名>のSELECTでエラー\n{e}\n{traceback.format_exc()}')
            return False, str(e)

        return True, rows
```

**規約:**
- コメントはすべて日本語
- 公開メソッドの戻り値は `(bool, value_or_error)` タプル
- SQLは複数行文字列で書く（可読性のため）
- バインド変数を使用してSQLインジェクションを防ぐ

### 4. `src/db/__init__.py` に登録

以下の2箇所を追加:

① ファイル先頭のimport群に追加:
```python
from .<module_name> import <ClassName>
```

② `Db.service_init()` の末尾に追加:
```python
self.<instance_name> = <ClassName>(log, conn, dict_return)
```

### 5. 作成・変更したすべてのファイルの内容を表示する
