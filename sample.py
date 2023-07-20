from src.kabusapi import KabusApi

## インスタンス生成&トークン発行(開発環境)
api = KabusApi('password')

# インスタンス生成&トークン発行(本番環境)
#api = KabusApi('password', production = True)

# トークン出力
print(api.token)

# トークン再取得
#api.auth.issue_token('password')
