"""
セットアップ確認スクリプト

新しいPCにSPAFTを導入した後、正しく設定できているかを確認する。
このスクリプトは src/ ディレクトリ内で実行すること。
  cd src
  python setup_check.py
"""
import sys
import importlib

# 確認結果の集計
ok_count = 0
ng_count = 0

def check_ok(message):
    '''チェックOKの表示'''
    global ok_count
    ok_count += 1
    print(f'  [OK] {message}')

def check_ng(message):
    '''チェックNGの表示'''
    global ng_count
    ng_count += 1
    print(f'  [NG] {message}')

def section(title):
    '''セクションヘッダーの表示'''
    print(f'\n{"=" * 50}')
    print(f'  {title}')
    print(f'{"=" * 50}')

# ==================================================
# 1. Pythonモジュールチェック
# ==================================================
section('1. Pythonモジュール')

REQUIRED_MODULES = [
    ('pymysql',       'pymysql'),
    ('requests',      'requests'),
    ('ntplib',        'ntplib'),
    ('catboost',      'catboost'),
    ('scikit-learn',  'sklearn'),
    ('pandas',        'pandas'),
    ('numpy',         'numpy'),
    ('tkcalendar',    'tkcalendar'),
]

for pip_name, import_name in REQUIRED_MODULES:
    try:
        importlib.import_module(import_name)
        check_ok(f'{pip_name} がインストールされている')
    except ImportError:
        check_ng(f'{pip_name} がインストールされていない → pip install {pip_name}')

# ==================================================
# 2. configファイルチェック
# ==================================================
section('2. configファイル')

try:
    import config
    check_ok('config.py が存在する')
except ModuleNotFoundError:
    check_ng('config.py が存在しない → src/config.py.sample を src/config.py にコピーして設定すること')
    print('\n設定が不完全なため、以降のチェックをスキップします。')
    print(f'\n結果: OK {ok_count}件 / NG {ng_count}件')
    sys.exit(1)

# 必須パラメータの存在チェック
REQUIRED_PARAMS = [
    ('DB_HOST',        'DBホスト名'),
    ('DB_USER',        'DBユーザー名'),
    ('DB_PASSWORD',    'DBパスワード'),
    ('DB_NAME',        'DB名'),
    ('API_PASSWORD',   'KabuStation APIパスワード'),
    ('TRADE_PASSWORD', '取引パスワード'),
    ('API_PRODUCTION', 'API環境フラグ'),
]

for param, description in REQUIRED_PARAMS:
    if hasattr(config, param):
        value = getattr(config, param)
        # サンプル値のままでないか確認
        if param == 'DB_PASSWORD' and value == 'password':
            check_ng(f'{param}（{description}）がサンプル値のまま → 実際のパスワードに変更すること')
        elif param == 'API_PASSWORD' and value == 'password':
            check_ng(f'{param}（{description}）がサンプル値のまま → KabuStationで設定したAPIパスワードに変更すること')
        elif param == 'TRADE_PASSWORD' and value == 'password':
            check_ng(f'{param}（{description}）がサンプル値のまま → 実際の取引パスワードに変更すること')
        else:
            check_ok(f'{param}（{description}）が設定されている')
    else:
        check_ng(f'{param}（{description}）が config.py に存在しない → config.py.sample を確認すること')

# ==================================================
# 3. KabuStation API疎通チェック
# ==================================================
section('3. KabuStation API疎通')

try:
    import requests as req

    # 接続先URLの決定
    if getattr(config, 'API_PRODUCTION', True):
        api_url = 'http://localhost:18080/kabusapi'
        env_label = '本番環境（ポート18080）'
    else:
        api_url = 'http://localhost:18081/kabusapi'
        env_label = '検証環境（ポート18081）'

    print(f'  接続先: {env_label}')

    # トークン発行チェック
    try:
        response = req.post(
            f'{api_url}/token',
            json={'APIPassword': config.API_PASSWORD},
            timeout=5
        )
        if response.status_code == 200:
            token = response.json().get('Token', '')
            if token:
                check_ok(f'KabuStation APIへの接続・トークン発行に成功した')
            else:
                check_ng('トークン発行レスポンスにTokenが含まれていない')
        elif response.status_code == 400:
            check_ng(f'APIパスワードが誤っている（HTTP 400） → config.py の API_PASSWORD を確認すること')
        else:
            check_ng(f'APIへの接続に失敗した（HTTP {response.status_code}）')
    except req.exceptions.ConnectionError:
        check_ng(f'KabuStationに接続できない → KabuStationが起動しているか確認すること（{env_label}）')
    except req.exceptions.Timeout:
        check_ng('KabuStation APIへの接続がタイムアウトした → KabuStationが起動しているか確認すること')

except Exception as e:
    check_ng(f'KabuStation APIチェック中にエラーが発生した: {e}')

# ==================================================
# 4. MySQL疎通・テーブルチェック
# ==================================================
section('4. MySQL疎通・テーブル')

REQUIRED_TABLES = [
    'api_process',
    'board',
    'buying_power',
    'errors',
    'holds',
    'listed',
    'ohlc',
    'orders',
]

try:
    import pymysql

    # 接続チェック
    try:
        conn = pymysql.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset='utf8mb4',
            connect_timeout=5
        )

        # バージョン確認
        with conn.cursor() as cursor:
            cursor.execute('SELECT VERSION()')
            mysql_version = cursor.fetchone()[0]

        major, minor = int(mysql_version.split('.')[0]), int(mysql_version.split('.')[1])
        if (major == 8 and minor in (0, 4)) or major > 8:
            check_ok(f'MySQLへの接続に成功した（{config.DB_HOST} / DB: {config.DB_NAME} / バージョン: {mysql_version}）')
        elif major == 8:
            check_ok(f'MySQLへの接続に成功した（バージョン: {mysql_version}） ※動作確認済みは 8.0 / 8.4')
        else:
            check_ng(f'MySQLのバージョンが対応外（{mysql_version}） → 8.0 または 8.4 を使用すること')

        # テーブル存在チェック
        with conn.cursor() as cursor:
            cursor.execute('SHOW TABLES')
            existing_tables = {row[0] for row in cursor.fetchall()}

        for table in REQUIRED_TABLES:
            if table in existing_tables:
                check_ok(f'テーブル "{table}" が存在する')
            else:
                check_ng(f'テーブル "{table}" が存在しない → sql/ddl/{table}.sql を実行すること')

        conn.close()

    except pymysql.err.OperationalError as e:
        error_code = e.args[0]
        if error_code == 2003:
            check_ng(f'MySQLに接続できない → MySQLが起動しているか、ホスト名・ポートを確認すること（{config.DB_HOST}）')
        elif error_code == 1045:
            check_ng('MySQLの認証に失敗した → config.py の DB_USER / DB_PASSWORD を確認すること')
        elif error_code == 1049:
            check_ng(f'データベース "{config.DB_NAME}" が存在しない → sql/db/spaft.sql を実行すること')
        else:
            check_ng(f'MySQLへの接続でエラーが発生した（コード: {error_code}）: {e}')

except ImportError:
    check_ng('pymysql がインストールされていないため、MySQLチェックをスキップした')

# ==================================================
# 結果サマリー
# ==================================================
print(f'\n{"=" * 50}')
print(f'  チェック結果: OK {ok_count}件 / NG {ng_count}件')
print(f'{"=" * 50}')

if ng_count == 0:
    print('  すべてのチェックが通過した。セットアップ完了！')
else:
    print(f'  {ng_count}件のNGがある。上記の [NG] 項目を修正すること。')
print()
