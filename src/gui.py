import config
import tkinter as tk
from base import Base
from datetime import datetime
from tkinter import messagebox
from tkcalendar import DateEntry

class StockOrderApp(Base):
    def __init__(self, root):
        super().__init__()
        self.root = root
        self.root.title('信用空売り決済注文')
        self.api_url = 'https://your-api-url.com'
        self.api_headers = {'Authorization': 'Bearer your_api_token'}  # 適切な認証情報に置き換える

        # ウィジェットの設定
        self.create_widgets()

    def create_widgets(self):
        # フォントサイズや揃え方の調整
        label_options = {'anchor': 'w', 'font': ('Arial', 13)}  # 左揃え
        entry_options = {'justify': 'right', 'font': ('Arial', 13)}  # 右揃え
        font_options = ('Arial', 11)

        # 横幅が項目の表示/非表示で変わらないように固定
        self.root.grid_columnconfigure(0, weight=1, minsize=200)
        self.root.grid_columnconfigure(1, weight=1, minsize=270)

        # 証券コード
        tk.Label(self.root, text='証券コード', **label_options).grid(row=0, column=0, sticky='w', padx=10, pady=(20, 5))
        self.stock_code_entry = tk.Entry(self.root, **entry_options, width=5, validate='key', validatecommand=(self.root.register(self.validate_stock_code), '%P'))
        self.stock_code_entry.grid(row=0, column=1, sticky='e', padx=(0, 15), pady=(20, 5))

        # 注文株数
        tk.Label(self.root, text='注文株数', **label_options).grid(row=1, column=0, sticky='w', padx=10, pady=5)
        self.qty_entry = tk.Entry(self.root, **entry_options, width=5, validate='key', validatecommand=(self.root.register(self.validate_qty), '%P'))
        self.qty_entry.insert(0, '100')  # デフォルト値を設定
        self.qty_entry.grid(row=1, column=1, sticky='e', padx=(0, 15), pady=5)

        # 証券取引所 (Exchange)
        tk.Label(self.root, text='証券取引所', **label_options).grid(row=2, column=0, sticky='w', padx=10, pady=5)
        self.exchange_var = tk.StringVar(self.root)
        self.exchange_var.set('東証')  # デフォルト値
        self.exchange_map = {
            '東証': 1,
            '名証': 3,
            '福証': 5,
            '札証': 6,
        }
        self.exchange_menu = tk.OptionMenu(self.root, self.exchange_var, *self.exchange_map.keys())
        self.exchange_menu.config(font=font_options)
        self.exchange_menu.grid(row=2, column=1, sticky='e', padx=(0, 15), pady=5)

        # 取引区分 (CashMargin)
        tk.Label(self.root, text='取引区分', **label_options).grid(row=3, column=0, sticky='w', padx=10, pady=5)
        self.cash_margin_var = tk.StringVar(self.root)
        self.cash_margin_var.set('返済信用')  # デフォルト値
        self.cash_margin_map = {
            '現物': 1,
            '新規信用': 2,
            '返済信用': 3,
        }
        self.cash_margin_menu = tk.OptionMenu(self.root, self.cash_margin_var, *self.cash_margin_map.keys(), command=self.update_cash_margin_state)
        self.cash_margin_menu.config(font=font_options)
        self.cash_margin_menu.grid(row=3, column=1, sticky='e', padx=(0, 15), pady=5)

        # 売買区分 (Side)
        tk.Label(self.root, text='売買区分', **label_options).grid(row=4, column=0, sticky='w', padx=10, pady=5)
        self.side_var = tk.StringVar(self.root)
        self.side_var.set('買')  # デフォルト値
        self.side_map = {
            '買': '2',
            '売': '1',
        }
        self.side_menu = tk.OptionMenu(self.root, self.side_var, *self.side_map.keys(), command=self.update_side_state)
        self.side_menu.config(font=font_options)
        self.side_menu.grid(row=4, column=1, sticky='e', padx=(0, 15), pady=5)

        # 信用区分 (MarginTradeType)
        self.margin_trade_type_label = tk.Label(self.root, text='信用区分', **label_options)
        self.margin_trade_type_label.grid(row=5, column=0, sticky='w', padx=10, pady=5)
        self.margin_trade_type_var = tk.StringVar(self.root)
        self.margin_trade_type_var.set('一般長期')  # デフォルト値
        self.margin_trade_type_map = {
            '制度': 1,
            '一般長期': 2,
            'デイトレ': 3
        }
        self.margin_trade_type_menu = tk.OptionMenu(self.root, self.margin_trade_type_var, *self.margin_trade_type_map.keys())
        self.margin_trade_type_menu.config(font=font_options)  # フォント設定
        self.margin_trade_type_menu.grid(row=5, column=1, sticky='e', padx=(0, 15), pady=5)

        # ポジション決済順 (ClosePositionOrder)
        self.close_position_order_label = tk.Label(self.root, text='ポジション決済順', **label_options)
        self.close_position_order_label.grid(row=6, column=0, sticky='w', padx=10, pady=5)
        self.close_position_order_var = tk.StringVar(self.root)
        self.close_position_order_var.set('日付(古い順),損益(高い順)')  # デフォルト値
        self.close_position_order_map = {
            '日付(古い順),損益(高い順)' : 0,
            '日付(古い順),損益(低い順)' : 1,
            '日付(新しい順),損益(高い順)' : 2,
            '日付(新しい順),損益(低い順)' : 3,
            '損益(高い順),日付(古い順)' : 4,
            '損益(高い順),日付(新しい順)' : 5,
            '損益(低い順),日付(古い順)' : 6,
            '損益(低い順),日付(新しい順)' : 7
        }
        self.close_position_order_menu = tk.OptionMenu(self.root, self.close_position_order_var, *self.close_position_order_map.keys())
        self.close_position_order_menu.config(font=font_options)  # フォント設定
        self.close_position_order_menu.grid(row=6, column=1, sticky='e', padx=(0, 15), pady=5)

        # 受渡区分 (DelivType)
        self.deliv_type_label = tk.Label(self.root, text='受渡区分', **label_options)
        self.deliv_type_label.grid(row=7, column=0, sticky='w', padx=10, pady=5)
        self.deliv_type_var = tk.StringVar(self.root)
        self.deliv_type_var.set('お預かり金')  # デフォルト値
        self.deliv_type_map = {
            'お預かり金': 2,
            'auマネーコネクト': 3,
            '現物売or信用新規': 0
        }
        self.deliv_type_menu = tk.OptionMenu(self.root, self.deliv_type_var, *self.deliv_type_map.keys())
        self.deliv_type_menu.config(font=font_options)
        self.deliv_type_menu.grid(row=7, column=1, sticky='e', padx=(0, 15), pady=5)
        # 今んところマネーコネクトは使う予定なく選択する必要がないので非表示、バックで全て制御するように
        self.deliv_type_label.grid_remove()
        self.deliv_type_menu.grid_remove()

        # 資産区分 (FundType)
        self.fund_type_label = tk.Label(self.root, text='資産区分', **label_options)
        self.fund_type_label.grid(row=8, column=0, sticky='w', padx=10, pady=5)
        self.fund_type_var = tk.StringVar(self.root)
        self.fund_type_var.set('信用買・売')  # デフォルト値
        self.fund_type_map = {
            '信用買・売': '11',
            '現物売': '  ',
            '保護': '02',
            '信用代用': 'AA'
        }
        self.fund_type_menu = tk.OptionMenu(self.root, self.fund_type_var, *self.fund_type_map.keys())
        self.fund_type_menu.config(font=font_options)
        self.fund_type_menu.grid(row=8, column=1, sticky='e', padx=(0, 15), pady=5)
        self.fund_type_menu.grid_remove()
        self.fund_type_label.grid_remove()

        # 口座区分 (AccountType)
        tk.Label(self.root, text='口座区分', **label_options).grid(row=9, column=0, sticky='w', padx=10, pady=5)
        self.account_type_var = tk.StringVar(self.root)
        self.account_type_var.set('特定')  # デフォルト値
        self.account_type_map = {
            '一般': 2,
            '特定': 4,
            '法人': 12,
        }
        self.account_type_menu = tk.OptionMenu(self.root, self.account_type_var, *self.account_type_map.keys())
        self.account_type_menu.config(font=font_options)
        self.account_type_menu.grid(row=9, column=1, sticky='e', padx=(0, 15), pady=5)
        # 今んところは特定しか使わないから事故らないようにdisabledに
        self.account_type_menu.config(state='disabled')

        # 執行条件 (FrontOrderType)
        tk.Label(self.root, text='執行条件', **label_options).grid(row=10, column=0, sticky='w', padx=10, pady=5)
        self.front_order_type_var = tk.StringVar(self.root)
        self.front_order_type_var.set('成行')  # デフォルト値
        self.front_order_type_map = {
            '成行': 10,
            '指値': 20
        }
        self.front_order_type_menu = tk.OptionMenu(self.root, self.front_order_type_var, *self.front_order_type_map.keys(), command=self.toggle_price_entry)
        self.front_order_type_menu.config(font=font_options)
        self.front_order_type_menu.grid(row=10, column=1, sticky='e', padx=(0, 15), pady=5)

        # 注文価格 (Price) - 成行の場合にのみ表示
        self.price_label = tk.Label(self.root, text='注文価格:', **label_options)
        self.price_entry = tk.Entry(self.root, **entry_options, width=10)
        self.price_label.grid(row=11, column=0, sticky='w', padx=10, pady=5)
        self.price_entry.grid(row=11, column=1, sticky='e', padx=(0, 15), pady=5)
        self.price_label.grid_forget()
        self.price_entry.grid_forget()

        # 有効期限 (ExpireDay) - 当日チェックボックス
        tk.Label(self.root, text='有効期限', **label_options).grid(row=13, column=0, sticky='w', padx=10, pady=5)
        self.expire_day_var = tk.BooleanVar(value=True)
        self.expire_day_checkbox = tk.Checkbutton(
            self.root, text='当日(時間外は翌営業日)', variable=self.expire_day_var, font=font_options, command=self.toggle_expire_day
        )
        self.expire_day_checkbox.grid(row=13, column=1, sticky='e', padx=(0, 15), pady=5)

        # 有効期限 (ExpireDay) - 日付指定カレンダー
        self.expire_day_entry = DateEntry(self.root, date_pattern='yyyy-mm-dd')
        self.expire_day_entry.grid(row=14, column=1, sticky='e', padx=(0, 15), pady=5)
        self.expire_day_entry.grid_remove()

        # 実行ボタン
        tk.Button(self.root, text='注文を送信', command=self.send_order, font=font_options).grid(row=15, column=0, columnspan=2, pady=15)

    def toggle_price_entry(self, selected_value):
        '''執行条件が成行の場合の注文価格テキストボックスの表示/非表示切り替え'''
        if selected_value == '成行':
            self.price_label.grid_forget()
            self.price_entry.grid_forget()
        else:
            self.price_label.grid(row=12, column=0, sticky='w', padx=10, pady=5)
            self.price_entry.grid(row=12, column=1, sticky='e', padx=(0, 15), pady=5)

    def toggle_expire_day(self):
        '''当日有効期限のチェックボックスの状態に応じてカレンダーの表示/非表示切り替え'''
        if self.expire_day_var.get():
            self.expire_day_entry.grid_remove()  # 非表示にする
        else:
            self.expire_day_entry.grid()  # 再表示する

    def update_cash_margin_state(self, selected_value):
        '''取引区分の選択肢に応じて他の選択肢の内容を切り替える'''
        if selected_value == '現物':
            # 信用区分を非表示
            self.margin_trade_type_menu.grid_remove()
            self.margin_trade_type_label.grid_remove()

            # 選択中の売買区分を取得し、買の場合
            if self.side_var.get() == '買':
                '''
                # 資産区分を保護にして再表示
                self.fund_type_var.set('保護')
                self.fund_type_menu.grid()
                self.fund_type_label.grid()
                '''
                # 保護が使えないので信用代用固定
                self.fund_type_var.set('信用代用')
                self.fund_type_menu.grid_remove()
                self.fund_type_label.grid_remove()

                # ポジション決済順を非表示にする
                self.close_position_order_label.grid_remove()
                self.close_position_order_menu.grid_remove()

            else:
                # 資産区分を現物売にして非表示
                self.fund_type_var.set('現物売')
                self.fund_type_menu.grid_remove()
                self.fund_type_label.grid_remove()

                # ポジション決済順を再表示
                self.close_position_order_label.grid()
                self.close_position_order_menu.grid()

        else:
            # 信用区分を再表示
            self.margin_trade_type_menu.grid()
            self.margin_trade_type_label.grid()

            # 資産区分を信用買・売にして非表示
            self.fund_type_var.set('信用買・売')
            self.fund_type_menu.grid_remove()
            self.fund_type_label.grid_remove()

            # 新規信用の場合
            if selected_value == '新規信用':
                # ポジション決済順を非表示にする
                self.close_position_order_label.grid_remove()
                self.close_position_order_menu.grid_remove()

            # 返済信用の場合
            else:
                # ポジション決済順を再表示
                self.close_position_order_label.grid()
                self.close_position_order_menu.grid()

    def update_side_state(self, selected_value):
        '''売買区分の選択肢に応じて他の選択肢の内容を切り替える'''
        cash_margin = self.cash_margin_var.get()
        if selected_value == '買':
            # 取引区分のチェック
            if cash_margin == '現物':
                # ポジション決済順を非表示にする
                self.close_position_order_label.grid_remove()
                self.close_position_order_menu.grid_remove()

                '''
                # 資産区分を保護にして再表示
                self.fund_type_var.set('保護')
                self.fund_type_menu.grid()
                self.fund_type_label.grid()
                '''
                # 保護が使えないので信用代用固定
                self.fund_type_var.set('信用代用')
                self.fund_type_menu.grid_remove()
                self.fund_type_label.grid_remove()

        # 売の場合
        else:
            # 取引区分のチェック
            if cash_margin == '現物':
                # ポジション決済順を再表示
                self.close_position_order_label.grid()
                self.close_position_order_menu.grid()

                # 資産区分を現物売にして非表示
                self.fund_type_var.set('現物売')
                self.fund_type_menu.grid_remove()
                self.fund_type_label.grid_remove()

    def validate_stock_code(self, stock_code):
        # 証券コードは文字と数字の入力を許可
        if len(stock_code) > 4:
            return False
        return True

    def validate_qty(self, qty):
        # 注文株数は数値のみ許可
        if not qty.isdigit() and qty != '':
            return False
        return True

    def send_order(self):
        # 入力値を取得
        stock_code = self.stock_code_entry.get()
        qty = self.qty_entry.get()
        exchange_label = self.exchange_var.get()
        side_label = self.side_var.get()
        cash_margin_label = self.cash_margin_var.get()
        margin_trade_type_label = self.margin_trade_type_var.get()
        close_position_order_label = self.close_position_order_var.get()
        deliv_type_label = self.deliv_type_var.get()
        fund_type_label = self.fund_type_var.get()
        account_type_label = self.account_type_var.get()
        front_order_type_label = self.front_order_type_var.get()
        price = self.price_entry.get()
        expire_day = self.expire_day_entry.get().replace('-', '')

        if not stock_code:
            messagebox.showerror('エラー', '証券コードを入力してください。')
            return
        if len(stock_code) > 4:
            messagebox.showerror('エラー', '証券コードは4桁以内で入力してください。')
            return
        if not qty:
            qty = 100
        try:
            qty = int(qty)
            exchange = self.exchange_map[exchange_label]
            side = self.side_map[side_label]
            cash_margin = self.cash_margin_map[cash_margin_label]
            margin_trade_type = self.margin_trade_type_map[margin_trade_type_label]
            close_position_order = self.close_position_order_map[close_position_order_label]
            deliv_type = self.deliv_type_map[deliv_type_label]
            fund_type = self.fund_type_map[fund_type_label]
            account_type = self.account_type_map[account_type_label]
            front_order_type = self.front_order_type_map[front_order_type_label]
        except ValueError:
            messagebox.showerror('エラー', '数値で指定する必要がある項目があります。')
            return

        if front_order_type_label == '指値' and not price:
            messagebox.showerror('エラー', '注文価格を入力してください。')
            return

        if price:
            try:
                price = float(price)
            except ValueError:
                messagebox.showerror('エラー', '注文価格は数値で入力してください。')
                return

        # 選択・入力した内容をそのまま使用できる項目を設定
        order_info = {
            'Symbol': str(stock_code),          # 証券コード
            'Exchange': exchange,               # 市場コード
            'SecurityType': 1,                  # 取引種別、1: 株式
            'Side': side,                       # 売買区分
            'CashMargin': cash_margin,          # 取引区分
            'FundType': fund_type,              # 資産区分
            'AccountType': account_type,        # 口座区分
            'Qty': qty,                         # 注文数量
            'FrontOrderType': front_order_type, # 執行条件
            'Password': config.TRADE_PASSWORD   # 取引パスワード
        }

        # 現物でない(信用の)場合は信用区分を設定、現物の場合は省略
        if cash_margin != 1:
            order_info['MarginTradeType'] = margin_trade_type

        # 受渡区分の設定
        # 現物買か信用返済の場合、資金の受渡・受取にお預かり金を選択
        if (cash_margin == 1 and side == '2') or (cash_margin == 3):
            order_info['DelivType'] = 2
        # それ以外の場合は指定なしを選択
        # 信用の場合、返済時に初めて計算される、現物売では買いと同じ資金で受け渡しが行われるため
        else:
            order_info['DelivType'] = 0

        # ポジション決済順の設定
        # 現物売か信用返済の場合のみ、選択したものを設定
        if (cash_margin == 1 and side == 1) or (cash_margin == 3):
            order_info['ClosePositionOrder'] = close_position_order

        # 注文価格の設定
        # 成行の場合は指定なし(0)を設定
        if front_order_type == 10:
            order_info['Price'] = 0
        # 指値の場合は入力した価格を設定
        else:
            order_info['Price'] = price

        # 有効期限の設定
        now = datetime.now()
        # 当日チェックボックスにチェックが入っているか
        if self.expire_day_var.get():
            # 現在時刻のチェック
            time_type = self.util.culc_time.exchange_time(now)
            # 大引け前の場合は当日の日付を指定
            if time_type != 5:
                order_info['ExpireDay'] = expire_day
            # それ以外の場合は翌営業日を指定
            else:
                order_info['ExpireDay'] = self.util.culc_time.next_exchange_workday(datetime.strptime(expire_day, "%Y%m%d")).strftime("%Y%m%d")
        # 入っていない場合は指定した日付をそのまま挿入
        else:
            order_info['ExpireDay'] = expire_day

        # 注文リクエスト送信
        result, response = self.service.trade.direct_order(order_info)
        if result:
            messagebox.showinfo('成功', f'注文が成功しました。\n受付注文番号: {response.get("OrderId", "不明")}')
        else:
            messagebox.showerror('エラー', f'注文が失敗しました。\n詳細: {response}')
            messagebox.showerror('エラー', order_info)

# アプリケーションの起動
if __name__ == '__main__':
    root = tk.Tk()
    app = StockOrderApp(root)
    root.mainloop()
