import csv
import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime

def get_stock_price(stock_code, start_date, end_date):
    '''
    指定期間内の株価を取得して成形して返す
    ※直近1年分しか取得できない

    Args:
        stock_code(int): 取得対象の証券コード
        start_date(str): 取得対象の開始日(最古の日)
        end_date(str): 取得対象の終了日(最新の日)

    '''
    # 引数チェック
    try:
        datetime(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
    except Exception as e:
        print(e)
        print(f'取得対象開始日が異常 開始日: {start_date}')
        return False

    try:
        datetime(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
    except Exception:
        print(f'取得対象終了日が異常 終了日: {end_date}')
        return False

    if start_date > end_date:
        print(f'取得対象開始日よりも終了日の日付の方が古い 開始日: {start_date}, 終了日: {end_date}')
        return False

    if end_date > datetime.now().strftime("%Y%m%d"):
        print(f'取得対象終了日が未来の日付になっている 終了日: {end_date}')
        return False

    if not isinstance(stock_code, int):
        print(f'証券コードが異常 証券コード: {stock_code}')
        return False

    # 株探から直近30営業日分のHTMLデータ取得
    table = get_kabutan(stock_code, 1)
    if table == False:
        return

    # HTMLからlist[dict]へ変換
    data_list = mold_stock_price(table)

    # 取得対象が1ぺージのデータで収まっているか
    if start_date > data_list[-1]['date_time']:
        shave_data_list = shave_data(data_list, start_date, end_date)
        return shave_data_list

    # 取得対象が1ページ目に一部含まれているか
    include_flag = False
    if end_date > data_list[-1]['date_time']:
        include_flag = True

    for page_num in range(2, 11):
        print(page_num)
        time.sleep(2)
        # 日付を遡って再取得
        table = get_kabutan(stock_code, page_num)
        if table == False:
            print(f'開始日のデータがサイトに存在しない可能性あり 開始日: {start_date}')
            return
        new_data_list = mold_stock_price(table)

        if not include_flag:
            data_list = []
            if end_date > new_data_list[-1]['date_time']:
                include_flag = True
                continue
        # これまでに取得したリストへ結合
        data_list += new_data_list
        # 開始日がこのページのデータに含まれていたらループ終了
        if start_date > new_data_list[-1]['date_time']:
            break
        elif page_num == 10:
            print(f'開始日のデータがサイトに存在しない 終了日: {start_date}')
            return False

    shave_data_list = shave_data(data_list, start_date, end_date)
    return shave_data_list

def get_kabutan(stock_code, page):
    '''
    指定した証券コード／ページの株価時系列データを株探から取得して返す

    Args:
        stock_code(int): 取得対象の証券コード
        page(int): 取得取得のページ

    Returns:
        table(bs4.element.Tag): 取得した時系列データのHTML(テーブル)要素

    '''
    # 引数チェック
    if not isinstance(stock_code, int):
        print(f'証券コードが異常 証券コード: {stock_code}')
        return False

    if not isinstance(page, int):
        print(f'ページ異数が異常 ページ数: {page}')
        return False

    # 取得処理
    r = requests.get(f'https://kabutan.jp/stock/kabuka?code={stock_code}&ashi=day&page={page}')
    soup = BeautifulSoup(r.content, 'lxml', from_encoding = 'UTF-8')
    table = soup.find('table', class_ = 'stock_kabuka_dwm')

    # 取得失敗
    if table == None:
        print(f'株探からの時系列データ取得処理に失敗 証券コード: {stock_code}, ページ数: {page}')
        return False

    return table

def mold_stock_price(table):
    '''
    株探から取得したHTMLのテーブルタグをdict型に成形する

    Args:
        table(bs4.element.Tag): 取得した時系列データのHTML(テーブル)要素

    Return:
        data_list(list[dict, dict...]): 成形した時系列データ

    '''
    data_list = []
    tbody = table.find('tbody')
    for tr in tbody.find_all('tr'):
        data_dict = {}
        data_dict['date_time'] = '20' + tr.find('th').text.replace('/', '')
        td = tr.find_all('td')
        data_dict['start_price'] = td[0].text.replace(',', '')
        data_dict['max_price'] = td[1].text.replace(',', '')
        data_dict['min_price'] = td[2].text.replace(',', '')
        data_dict['end_price'] = td[3].text.replace(',', '')
        data_dict['volume'] = td[6].text.replace(',', '')
        data_list.append(data_dict)
    return data_list

def shave_data(data_list, start_date, end_date):
    '''
    時系列データから指定期間内のデータのみ切り出す

    Args:
        data_list(list[dict, dict...]): 時系列データ
        start_date(str): 取得対象の開始日(最古の日)
        end_date(str): 取得対象の終了日(最新の日)

    Returns:
        list[dict, dict...]: 対象外のデータを削ぎ落した時系列データ
    '''
    start_index = -1
    end_index = -1

    # 最新の日付から辿って
    for index, data in enumerate(data_list):
        start_index = index
        if data['date_time'] == end_date:
            break

        if data['date_time'] < end_date:
            start_index -= 1
            break

    for index, data in enumerate(reversed(data_list)):
        end_index = len(data_list) - 1 - index
        if data['date_time'] == start_date:
            break

        if data['date_time'] > start_date:
            end_index += 1
            break

    return data_list[start_index:end_index+1]

def list_of_dicts_to_csv(data_list, file_name):
    '''dict型のデータをCSV出力する'''

    # リストが空の場合は何もしない
    if not data_list:
        return

    # CSVファイルを書き込みモードで開く
    with open(file_name, 'w', newline='') as csvfile:
        # カラム名を取得するために最初の辞書のキーを使用
        fieldnames = data_list[0].keys()
        # DictWriterを作成し、カラム名を指定
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        # カラム名を書き込む
        writer.writeheader()
        # 各辞書をCSVファイルに書き込む
        for row in data_list:
            writer.writerow(row)


if __name__ == '__main__':

    for code in [1579,1360,1580,1458,1459,1365,1366,1456,1570,1571,1357,1358]:
        stock_code = code
        start_date = '20230501'
        end_date = '20240430'

        result = get_stock_price(stock_code, start_date, end_date)
        list_of_dicts_to_csv(result, f'../../csv/{stock_code}_{start_date}to{end_date}.csv')