import yfinance as yf
from datetime import datetime

def check_magic_nine_today(ticker_symbol):
    today = datetime.today().strftime('%Y-%m-%d')
    try:
        data = yf.download(ticker_symbol)
        up_count = 0
        down_count = 0
        for i in range(4, len(data)):
            if data['Close'][i] > data['Close'][i - 4]:
                up_count += 1
                if up_count == 9:
                    return "上涨九转"
                down_count = 0
            elif data['Close'][i] < data['Close'][i - 4]:
                down_count += 1
                if down_count == 9:
                    return "下跌九转"
                up_count = 0
            else:
                up_count = 0
                down_count = 0
        return "未出现神奇九转"
    except:
        return "获取数据失败，无法判断"

# 使用示例，这里以MSFT（微软）股票为例
print(check_magic_nine_today("002657.SZ"))