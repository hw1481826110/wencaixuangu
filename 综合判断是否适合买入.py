import pandas as pd
import numpy as np
import yfinance as yf
import talib
import requests

# 设置代理
proxy = 'http://127.0.0.1:7897'


def format_stock_code(input_code):
    """
    将输入的股票代码转换为 yfinance 所需的格式
    如果输入格式为“SZ001278”或“SH600000”，则转换为“001278.SZ”或“600000.SH”
    如果输入中已经包含"."，则认为已经是正确格式
    """
    code = input_code.strip()
    if "." in code:
        return code
    if code.upper().startswith("SZ"):
        return code[2:] + ".SZ"
    elif code.upper().startswith("SH"):
        return code[2:] + ".SH"
    else:
        # 如果没有前缀，默认视为深圳股票
        return code + ".SZ"


def get_stock_data(stock_code, period='1y'):
    """
    获取指定股票的历史数据
    """
    proxy = 'http://127.0.0.1:7890'
    df = yf.download(stock_code, period=period)
    return df


def calculate_indicators(df):
    """
    根据历史数据计算MACD、KDJ和RSI指标
    """
    # 确保数据为一维数组
    close = df['Close'].values.flatten()
    high = df['High'].values.flatten()
    low = df['Low'].values.flatten()

    # 计算 MACD
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    df['MACD'] = macd
    df['MACD_signal'] = macdsignal

    # 计算 KDJ 指标，利用 STOCH 得到 %K 和 %D，再计算 %J = 3 * %K - 2 * %D
    slowk, slowd = talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowk_matype=0,
                               slowd_period=3, slowd_matype=0)
    df['KDJ_K'] = slowk
    df['KDJ_D'] = slowd
    df['KDJ_J'] = 3 * slowk - 2 * slowd

    # 计算 RSI 指标，常用周期为14
    df['RSI'] = talib.RSI(close, timeperiod=14)

    return df


def evaluate_signals(df):
    """
    根据最新的指标值判断各项技术信号，并综合评分
    """
    latest = df.iloc[-1]
    score = 0
    signals = {}

    # MACD判断：MACD大于信号线看涨
    macd_val = float(latest['MACD'].iloc[0]) if isinstance(latest['MACD'], pd.Series) else float(latest['MACD'])
    macd_signal_val = float(latest['MACD_signal'].iloc[0]) if isinstance(latest['MACD_signal'], pd.Series) else float(
        latest['MACD_signal'])
    if macd_val > macd_signal_val:
        signals['MACD'] = "看涨"
        score += 1
    else:
        signals['MACD'] = "看跌"

    # KDJ判断：K值大于D值看涨
    kdj_k_val = float(latest['KDJ_K'].iloc[0]) if isinstance(latest['KDJ_K'], pd.Series) else float(latest['KDJ_K'])
    kdj_d_val = float(latest['KDJ_D'].iloc[0]) if isinstance(latest['KDJ_D'], pd.Series) else float(latest['KDJ_D'])
    if kdj_k_val > kdj_d_val:
        signals['KDJ'] = "看涨"
        score += 1
    else:
        signals['KDJ'] = "看跌"

    # RSI判断：RSI < 30为超卖买入信号；RSI > 70为超买卖出信号；否则中性
    rsi_val = float(latest['RSI'].iloc[0]) if isinstance(latest['RSI'], pd.Series) else float(latest['RSI'])
    if rsi_val < 30:
        signals['RSI'] = "超卖，买入信号"
        score += 1
    elif rsi_val > 70:
        signals['RSI'] = "超买，卖出信号"
    else:
        signals['RSI'] = "中性"

    return signals, score


def get_chinese_name(stock_code):
    """
    使用新浪财经接口获取股票的中文名称
    """
    if stock_code.endswith('.SZ'):
        sina_code = 'sz' + stock_code[:-3]
    elif stock_code.endswith('.SH'):
        sina_code = 'sh' + stock_code[:-3]
    else:
        return '未知名称'
    url = f'http://hq.sinajs.cn/list={sina_code}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.text
            parts = data.split('=')[1].split(',')
            if len(parts) > 0:
                name = parts[0].strip('"')
                return name
    except Exception as e:
        print(f"获取股票中文名称出错: {e}")
    return '未知名称'


def evaluate_stock(input_code):
    """
    对单个股票进行评测，返回一个结果字典
    """
    formatted_code = format_stock_code(input_code)
    result = {
        "原始股票代码": input_code,
        "转换后股票代码": formatted_code,
        "股票名称": "",
        "MACD信号": None,
        "KDJ信号": None,
        "RSI信号": None,
        "综合评分": None,
        "评测结果": None,
        "备注": ""
    }

    result["股票名称"] = get_chinese_name(formatted_code)

    print(f"正在获取 {formatted_code} 的数据...")
    df = get_stock_data(formatted_code)
    if df.empty:
        result["备注"] += "数据获取失败"
        print(f"{formatted_code} 数据获取失败，请检查股票代码或网络连接。")
        return result

    try:
        df = calculate_indicators(df)
        signals, score = evaluate_signals(df)
    except Exception as e:
        result["备注"] += f"计算出错：{e}"
        print(f"{formatted_code} 计算指标时出错：{e}")
        return result

    result["MACD信号"] = signals.get("MACD", "")
    result["KDJ信号"] = signals.get("KDJ", "")
    result["RSI信号"] = signals.get("RSI", "")
    result["综合评分"] = score
    result["评测结果"] = "建议买入" if score >= 2 else "建议观望或卖出"

    print(f"{formatted_code}（{result['股票名称']}）评测完成：综合评分 {score}，结果：{result['评测结果']}")
    return result


def main():
    print("请输入多个股票代码（每行一个），")
    print("如果某一行为空白则会自动跳过，")
    print("输入 '结束' 表示输入完毕。")

    codes = []
    while True:
        code = input()
        # 如果输入了"结束"，则退出输入循环
        if code.strip() == "结束":
            break
        # 跳过空白行
        if code.strip() == "":
            continue
        codes.append(code.strip())

    if not codes:
        print("未输入股票代码，程序退出。")
        return

    results = []
    for code in codes:
        res = evaluate_stock(code)
        results.append(res)

    # 将评测结果写入 CSV 文件
    df_result = pd.DataFrame(results)
    output_file = "股票评测结果.csv"
    df_result.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n所有结果已写入 {output_file}")


if __name__ == "__main__":
    main()
