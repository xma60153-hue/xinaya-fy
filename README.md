# xinaya-fy 股票量价分析

一个基于 Streamlit 和 Yahoo Finance 的最小量价分析页面。输入股票代码、选择时间范围与日/周/月图表频率，查看 K 线、成交量、5/20 日均线及 RSI。均线和 RSI 均按交易日计算；周/月图由日线汇总，成交量为当期合计。

## 运行

建议使用 Python 3.10 或更新版本：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

浏览器打开 Streamlit 显示的本地地址（通常为 http://localhost:8501）。默认代码 AAPL；沪市代码示例 `600519.SS`，深市示例 `000001.SZ`。数据需要连接 Yahoo Finance；行情是否提供及延迟情况由数据源决定。网络或代码错误时页面会显示提示。刷新后最多缓存行情五分钟。价格使用 yfinance 的自动调整数据，适合趋势观察，不能直接代表实时交易报价。

RSI 使用 Wilder 平滑（首个完整窗口的简单平均作初值）；连续上涨对应 100，连续无涨跌对应 50。展示仅供学习与研究。
