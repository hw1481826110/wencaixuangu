import pywencai
import pandas as pd
import numpy as np
import yfinance as yf
import talib

# 设置 pandas 显示选项，以完整显示数据
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)


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
    elif code.startswith("30") or  code.startswith("00"):
        return code + ".SZ"
    elif code.upper().startswith("SH"):
        return code[2:] + ".SS"
    elif code.startswith("60") :
        return code + ".SS"
    elif code.startswith("60") or code.startswith("68"):
        return code + ".SS"
    else:
        # 其他情况默认视为深圳股票
        return code + ".BJ"


def get_stock_data(stock_code, period='1y'):
    """
    获取指定股票的历史数据，添加重试机制
    """
    max_retries = 5
    retries = 0
    while retries < max_retries:
        try:
            df = yf.download(stock_code, period=period)
            if not df.empty:
                # print(df)
                return df
        except Exception as e:
            print(f"获取 {stock_code} 数据失败，第 {retries + 1} 次重试，错误信息: {e}")
        retries += 1
    print(f"超过 {max_retries} 次尝试，仍无法获取 {stock_code} 数据。")
    return pd.DataFrame()


def calculate_indicators(df):
    """
    根据历史数据计算MACD、KDJ、RSI、BOLL、DMI等指标
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

    # 计算 BOLL 指标
    upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
    df['BOLL_upper'] = upper
    df['BOLL_middle'] = middle
    df['BOLL_lower'] = lower

    # 计算 DMI 指标
    df['ADX'] = talib.ADX(high, low, close, timeperiod=14)
    df['+DI'] = talib.PLUS_DI(high, low, close, timeperiod=14)
    df['-DI'] = talib.MINUS_DI(high, low, close, timeperiod=14)

    return df


def evaluate_signals(df):
    """
    根据最新的指标值判断各项技术信号，并综合评分
    """
    latest = df.iloc[-1]
    score = 0
    signals = {}

    # MACD判断：MACD大于信号线看涨
    macd_val = float(latest['MACD'])
    macd_signal_val = float(latest['MACD_signal'])
    if macd_val > macd_signal_val:
        signals['MACD'] = "看涨"
        score += 1
    else:
        signals['MACD'] = "看跌"

    # KDJ判断：K值大于D值看涨
    kdj_k_val = float(latest['KDJ_K'])
    kdj_d_val = float(latest['KDJ_D'])
    if kdj_k_val > kdj_d_val:
        signals['KDJ'] = "看涨"
        score += 1
    else:
        signals['KDJ'] = "看跌"

    # RSI判断：RSI < 30为超卖买入信号；RSI > 70为超买卖出信号；否则中性
    rsi_val = float(latest['RSI'])
    if rsi_val < 30:
        signals['RSI'] = "超卖，买入信号"
        score += 1
    elif rsi_val > 70:
        signals['RSI'] = "超买，卖出信号"
    else:
        signals['RSI'] = "中性"

    # BOLL判断：收盘价突破上轨看涨
    close_val = float(latest['Close'])
    boll_upper_val = float(latest['BOLL_upper'])
    if close_val > boll_upper_val:
        signals['BOLL'] = "看涨"
        score += 1
    else:
        signals['BOLL'] = "中性"

    # DMI判断：+DI 大于 -DI 且 ADX 上升看涨
    plus_di_val = float(latest['+DI'])
    minus_di_val = float(latest['-DI'])
    adx_val = float(latest['ADX'])
    prev_adx_val = float(df.iloc[-2]['ADX']) if len(df) > 1 else 0
    if plus_di_val > minus_di_val and adx_val > prev_adx_val:
        signals['DMI'] = "看涨"
        score += 1
    else:
        signals['DMI'] = "中性"

    return signals, score


def evaluate_stock(row):
    """
    对单个股票进行评测，返回一个结果字典
    """
    stock_code = row['code'] if 'code' in row else row['股票代码']
    formatted_code = format_stock_code(stock_code)
    result = {
        "原始股票代码": stock_code,
        "转换后股票代码": formatted_code,
        "股票名称": row['股票简称'],
        "MACD信号": None,
        "KDJ信号": None,
        "RSI信号": None,
        "BOLL信号": None,
        "DMI信号": None,
        "综合评分": None,
        "评测结果": None,
        "备注": "",
        "主力持仓成本": row.get('主力持仓成本', '暂无数据'),
        "平均成本": row.get('平均成本', '暂无数据')
    }

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
    result["BOLL信号"] = signals.get("BOLL", "")
    result["DMI信号"] = signals.get("DMI", "")
    result["综合评分"] = score
    result["评测结果"] = "建议买入" if score >= 3 else "建议观望或卖出"

    print(f"{formatted_code}（{result['股票名称']}）评测完成：综合评分 {score}，结果：{result['评测结果']}")
    return result


def main():
    # 出现MACD水上二次金叉的股票
    res = pywencai.get(query='当日最低价超过前三日下影线，且之前横盘时间大于三天', sleep=3)
    if res.empty:
        print("未获取到符合条件的股票代码，程序退出。")
        return

    # 控制台输出问财数据
    print("问财获取的数据如下：")
    print(res)

    results = []
    for index, row in res.iterrows():
        res = evaluate_stock(row)
        # 合并问财数据和评测结果
        combined_result = {**row.to_dict(), **res}
        results.append(combined_result)

    # 将评测结果写入 CSV 文件
    df_result = pd.DataFrame(results)
    output_file = "股票评测结果.csv"
    df_result.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n所有结果已写入 {output_file}")


if __name__ == "__main__":
    # while True:
    main()
