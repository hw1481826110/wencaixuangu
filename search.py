import pywencai
import pandas as pd

# 设置 pandas 显示选项，以完整显示数据
pd.set_option('display.max_rows', None)  # 显示所有行
pd.set_option('display.max_columns', None)  # 显示所有列
pd.set_option('display.width', None)  # 不限制显示宽度
pd.set_option('display.max_colwidth', None)  # 不限制列宽

# res = pywencai.get(query='看多指标最多的深证股票', sleep=3)
res = pywencai.get(query='出现MACD水上二次金叉的深证股票', sleep=3)

print(res)