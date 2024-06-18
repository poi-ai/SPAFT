# シミュレーションをする銘柄
STOCK_CODE = [1570,9432,8411,4755,8306,7201,9501,7203] # 1570 日経レバ、9432 NTT、8411 みずほ、4755 楽天、8306 三菱UFJ、7201 日産、9501 東電、7203 トヨタ

# シミュレーション日(yyyy-mm-dd)
TARGET_DATE = ['2024-06-18']

# シミュレーション時間(HH:MM)
START_TIME = '09:00'
END_TIME = '15:00'

# 余力
BUY_POWER = 1000000

# 利確/損切ライン(pips)
SECURING_BENEFIT_BORDER = [i for i in range(1,11)]
LOSS_CUT_BORDER = [i for i in range(1,11)]

# 利確/損切後の再注文(利確/損切り額の何pips下に入れるか)
REORDER_LINE = [i for i in range(1,11)]

# 呼値 TODO いずれAPIからとってきたいが遅延になるから最初の一回だけにしたい
PRICE_RANGE = 1
# 1570 5
# 8411,7203 1
# 8306 0.5
# 9432,4755,7201,9501 0.1

# 売買単位 TODO こっちもいずれAPIからとってきたいが遅延になるから最初の一回だけにしたい
UNIT_NUM = 100
# 1570 1
# 9432,8411,4755,8306,7201,9501,7213 100
