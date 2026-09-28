"""股票量价、日均线与 RSI 的 Streamlit 页面。"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

st.set_page_config(page_title="股票量价分析", layout="wide")
st.title("股票量价关系 · 均线 · RSI")
st.caption("输入 Yahoo Finance 股票代码，例如 AAPL、600519.SS、000001.SZ。行情可能延迟。")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    ticker = st.text_input("股票代码", value="AAPL").strip().upper()
with col2:
    period = st.selectbox("时间范围", ["3mo", "6mo", "1y", "2y", "5y"], index=1)
with col3:
    interval = st.selectbox("图表频率", ["1d", "1wk", "1mo"], index=0)
show_ma = st.checkbox("显示 5/20 日均线", value=True)
show_rsi = st.checkbox("显示 RSI", value=True)
rsi_period = st.number_input("RSI 周期（日）", min_value=5, max_value=50, value=14)


@st.cache_data(ttl=300)
def fetch_data(symbol: str, selected_period: str) -> pd.DataFrame:
    # 始终下载日线，保证周/月图中的 MA5/MA20 仍表示交易日。
    data = yf.download(symbol, period=selected_period, interval="1d", auto_adjust=True,
                       progress=False, threads=False, multi_level_index=False)
    if data is None or data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    required = ["Open", "High", "Low", "Close", "Volume"]
    if any(column not in data for column in required):
        raise ValueError("行情数据缺少 OHLCV 字段")
    data = data[required].apply(pd.to_numeric, errors="coerce").dropna()
    data.index = pd.to_datetime(data.index)
    return data.sort_index()


def compute_indicators(data: pd.DataFrame, length: int) -> pd.DataFrame:
    data = data.copy()
    close = data["Close"]
    data["MA5"] = close.rolling(5, min_periods=5).mean()
    data["MA20"] = close.rolling(20, min_periods=20).mean()
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    # Wilder 平滑，以首个完整窗口的简单平均作为初值。
    avg_gain = pd.Series(float("nan"), index=data.index)
    avg_loss = pd.Series(float("nan"), index=data.index)
    if len(data) > length:
        gain = gains.iloc[1:length + 1].mean()
        loss = losses.iloc[1:length + 1].mean()
        avg_gain.iloc[length] = gain
        avg_loss.iloc[length] = loss
        for i in range(length + 1, len(data)):
            gain = (gain * (length - 1) + gains.iloc[i]) / length
            loss = (loss * (length - 1) + losses.iloc[i]) / length
            avg_gain.iloc[i] = gain
            avg_loss.iloc[i] = loss
    ratio = avg_gain / avg_loss.replace(0, float("nan"))
    data["RSI"] = 100 - 100 / (1 + ratio)
    data.loc[(avg_loss == 0) & (avg_gain > 0), "RSI"] = 100.0
    data.loc[(avg_loss == 0) & (avg_gain == 0), "RSI"] = 50.0
    return data


def display_frequency(data: pd.DataFrame, frequency: str) -> pd.DataFrame:
    if frequency == "1d":
        return data
    rule = {"1wk": "W-FRI", "1mo": "ME"}[frequency]
    ohlcv = data.resample(rule).agg({"Open": "first", "High": "max", "Low": "min",
                                      "Close": "last", "Volume": "sum"})
    indicators = data[["MA5", "MA20", "RSI"]].resample(rule).last()
    result = ohlcv.join(indicators).dropna(subset=["Open", "High", "Low", "Close"])
    # 用该周/月实际最后一个交易日标记，避免未来的日历结束日。
    result.index = data.index.to_series().resample(rule).last().loc[result.index].to_numpy()
    return result


if not ticker:
    st.info("请输入股票代码。")
    st.stop()
try:
    daily = fetch_data(ticker, period)
except Exception as exc:
    st.error(f"行情获取失败：{exc}。请检查股票代码、网络连接或稍后重试。")
    st.stop()
if daily.empty:
    st.warning("未取得行情数据。请核对 Yahoo Finance 股票代码或稍后重试。")
    st.stop()

daily = compute_indicators(daily, int(rsi_period))
data = display_frequency(daily, interval)
if len(daily) < 20:
    st.info("数据少于 20 个交易日，20 日均线暂不可用。")
if len(daily) <= rsi_period:
    st.info("数据不足，RSI 暂不可用。")

rows = 3 if show_rsi else 2
fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.035,
                    row_heights=[0.55, 0.22, 0.23] if show_rsi else [0.72, 0.28])
fig.add_trace(go.Candlestick(x=data.index, open=data.Open, high=data.High,
                             low=data.Low, close=data.Close, name="价格"), row=1, col=1)
if show_ma:
    for column, color in [("MA5", "#e7a638"), ("MA20", "#4986d4")]:
        fig.add_trace(go.Scatter(x=data.index, y=data[column], mode="lines",
                                 name=column + "（日）", line=dict(color=color, width=1.7)), row=1, col=1)
colors = ["#d95c5c" if close < opening else "#44a787"
          for opening, close in zip(data.Open, data.Close)]
fig.add_trace(go.Bar(x=data.index, y=data.Volume, marker_color=colors, name="成交量"), row=2, col=1)
if show_rsi:
    fig.add_trace(go.Scatter(x=data.index, y=data.RSI, mode="lines", name=f"RSI ({rsi_period}日)",
                             line=dict(color="#9365b8")), row=3, col=1)
    for threshold in (30, 70):
        fig.add_hline(y=threshold, line_dash="dot", line_color="gray", row=3, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)
fig.update_yaxes(title_text="价格", row=1, col=1)
fig.update_yaxes(title_text="成交量", row=2, col=1)
fig.update_layout(height=800 if show_rsi else 650, xaxis_rangeslider_visible=False,
                  hovermode="x unified", legend=dict(orientation="h", y=1.03),
                  margin=dict(l=30, r=20, t=45, b=25))
st.plotly_chart(fig, width="stretch")
st.caption(f"{ticker} · {daily.index.min():%Y-%m-%d} 至 {daily.index.max():%Y-%m-%d} · "
           "自动调整价格；周/月图由日线汇总，均线和 RSI 始终按交易日计算。成交量为该周期合计。")
