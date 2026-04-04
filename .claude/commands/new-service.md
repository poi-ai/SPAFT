# 新規Serviceクラスの作成

引数で指定されたクラス名の新しい Service クラスを作成し、必要な場所に登録する。

クラス名: $ARGUMENTS

---

以下の手順で実装すること。

## 手順

### 1. `src/service/__init__.py` を読んで既存パターンを確認する

### 2. `src/service/<snake_case_name>.py` を新規作成

以下のテンプレートに従うこと:

```python
import traceback
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from service_base import ServiceBase

class <ClassName>(ServiceBase):
    '''
    <このクラスの目的を日本語で1〜2行で説明>
    '''

    def __init__(self, api_headers, api_url, ws_url, conn):
        '''
        初期設定処理

        Args:
            api_headers(dict): KabusAPIのリクエストで使用する認証用ヘッダー
            api_url(str): KabusAPIのリクエストで使用するエンドポイント
            ws_url(str): WebSocketのエンドポイント
            conn(pymysql.Conn): MySQLへの接続情報
                ※APIもDBも使わない場合はFalseを渡すこと

        '''
        super().__init__(api_headers, api_url, ws_url, conn)

    def <method_name>(self):
        '''
        <メソッドの目的を日本語で説明>

        Returns:
            result(bool): 実行結果 True: 成功、False: 失敗
            value(型): <成功時の戻り値の説明>
                失敗時はエラーメッセージ(str)を返す
        '''
        try:
            # 処理内容
            pass

        except Exception as e:
            self.error_output('<処理名>でエラー', e, traceback.format_exc())
            return False, str(e)

        return True, value
```

**規約:**
- コメント・ログメッセージはすべて日本語
- 公開メソッドの戻り値は `(bool, value_or_error)` タプル
- エラー処理は `self.error_output(message, e, traceback.format_exc())`
- APIを使わない場合は `super().__init__(False, False, False, False)`
- DBを使わない場合は `conn` に `False` を渡す

### 3. `src/service/__init__.py` に登録

以下の2箇所を追加:

① ファイル先頭のimport群に追加:
```python
from .<module_name> import <ClassName>
```

② `Service.__init__()` の末尾に追加:
```python
# <このクラスの目的を日本語で一言>
self.<instance_name> = <ClassName>(api_headers, api_url, ws_url, conn)
```

### 4. 作成・変更したファイルの内容を表示する
