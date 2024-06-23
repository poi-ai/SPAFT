import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import japanize_matplotlib  # ヒートマップの日本語表示に必要なので消さない

def generate_heatmap(stock_code, date, output_filename):
    # CSVデータを読み込み
    df = pd.read_csv('simulation_result.csv', encoding = 'utf-8')

    # データをフィルタリング
    filtered_data = df[(df['銘柄コード'] == stock_code) & (df['日付'] == date)]

    if filtered_data.empty:
        print(f"No data found for stock code {stock_code} on date {date}.")
        return

    # ヒートマップを作成
    pivot_table = filtered_data.pivot("損切りボーダー", "利確ボーダー", "収益").iloc[::-1]
    plt.figure(figsize=(7, 5))
    sns.heatmap(pivot_table, annot=True, fmt="g", cmap='viridis')
    plt.title(f"Stock Code: {stock_code}, Date: {date}")
    plt.xlabel("利確ボーダー")
    plt.ylabel("損切りボーダー")
    plt.savefig(output_filename)
    plt.close()

def process_multiple_stock_dates(stock_dates):
    counter = 1
    for stock_code, date in stock_dates:
        generate_heatmap(stock_code, date, f'{counter}.png')
        counter+=1

# 使用例
stock_dates = [
    (1570, '2024/6/10'),
    (9432, '2024/6/10'),
    (9432, '2024/6/11'),
    (1570, '2024/6/11'),
    (9432, '2024/6/12'),
    (1570, '2024/6/12'),
    (9432, '2024/6/13'),
    (1570, '2024/6/13'),
    (9432, '2024/6/14'),
    (1570, '2024/6/14'),
    (9432, '2024/6/17'),
    (8306, '2024/6/17'),
    (1570, '2024/6/17'),
    (9501, '2024/6/17'),
    (7203, '2024/6/17'),
    (9432, '2024/6/18'),
    (8306, '2024/6/18'),
    (7203, '2024/6/18'),
    (1570, '2024/6/18'),
    (9501, '2024/6/18'),
    (1570, '2024/6/19'),
    (8306, '2024/6/19'),
    (9432, '2024/6/19'),
    (9501, '2024/6/19'),
    (7203, '2024/6/19'),
    (1570, '2024/6/20'),
    (9432, '2024/6/20'),
    (8306, '2024/6/20'),
    (7203, '2024/6/20'),
    (9501, '2024/6/20'),
    (1570, '2024/6/21'),
    (9432, '2024/6/21'),
    (7203, '2024/6/21'),
    (9501, '2024/6/21'),
    (8306, '2024/6/21')
]

process_multiple_stock_dates(stock_dates)
