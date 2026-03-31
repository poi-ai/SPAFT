# 新規KabuStation APIラッパークラスの作成

引数で指定されたクラス名の新しい KabuStation API ラッパークラスを作成し、必要な場所に登録する。

クラス名（対応するAPIカテゴリ名）: $ARGUMENTS

---

## 手順

### 1. `src/kabusapi/__init__.py` を読んで既存パターンを確認する

### 2. `src/kabusapi/<snake_case_name>.py` を新規作成

以下のテンプレートに従うこと:

```python
import requests
import traceback
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class <ClassName>():
    '''
    KabuStation API の <カテゴリ名> に関するリクエストを行うクラス
    '''

    def __init__(self, api_headers, api_url, log):
        '''
        初期設定処理

        Args:
            api_headers(dict): 認証ヘッダー {'X-API-KEY': token}
            api_url(str): APIエンドポイント http://localhost:18080/kabusapi
            log(Log): ログクラスのインスタンス

        '''
        self.api_headers = api_headers
        self.api_url = api_url
        self.log = log

    def <method_name>(self, <params>):
        '''
        <APIの目的を日本語で説明>

        KabuStation API: <HTTP_METHOD> /kabusapi/<endpoint>

        Args:
            <param>(型): <説明>

        Returns:
            result(bool): 実行結果 True: 成功、False: 失敗
            response(dict) or error_message(str): レスポンスデータ or エラーメッセージ
        '''
        try:
            url = f'{self.api_url}/<endpoint>'
            r = requests.<get_post_put_delete>(url, headers=self.api_headers)

        except Exception as e:
            self.log.error(f'<処理名>でエラー\n{e}\n{traceback.format_exc()}')
            return False, str(e)

        if r.status_code != 200:
            self.log.error(f'<処理名> HTTPエラー: {r.status_code}\n{r.content}')
            return False, f'{r.status_code}'

        return True, r.json()
```

**規約:**
- コメントはすべて日本語
- URL構築は `f'{self.api_url}/<endpoint>'` パターン（ハードコード禁止）
- HTTPエラー時は `(False, ステータスコード文字列)` を返す
- 例外発生時は `(False, エラーメッセージ)` を返す
- ログメッセージは日本語
- レート制限に注意（発注系は5req/秒、情報系は10req/秒）

### 3. `src/kabusapi/__init__.py` に登録

以下の2箇所を追加:

① ファイル先頭のimport群に追加:
```python
from .<module_name> import <ClassName>
```

② `KabusApi.service_init()` の末尾に追加:
```python
# <このクラスの目的を日本語で一言>
self.<instance_name> = <ClassName>(api_headers, api_url, log)
```

### 4. 作成・変更したファイルの内容を表示する
