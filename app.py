import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. 配置 ---
st.set_page_config(page_title="DAT.co Monitor", layout="wide")
genai.configure(api_key="你的_API_KEY") # 記得填入你的 Key

# --- 2. 參數 (MSTR) ---
BTC_HOLDINGS = 252220  
SHARES_OUTSTANDING = 224440000 

st.title("🚀 MSTR Premium to NAV Tracker")

# --- 3. 獲取數據 (無敵對齊版) ---
@st.cache_data(ttl=600)
def fetch_data():
    mstr_raw = yf.download("MSTR", period="1y", interval="1d", auto_adjust=True)
    btc_raw = yf.download("BTC-USD", period="1y", interval="1d", auto_adjust=True)
    return mstr_raw, btc_raw

mstr_raw, btc_raw = fetch_data()

if mstr_raw.empty or btc_raw.empty:
    st.warning("⚠️ API 限流中，請稍候重整網頁。")
else:
    # 移除多層索引 (yfinance v1.2+ 的新問題)
    if isinstance(mstr_raw.columns, pd.MultiIndex):
        mstr_raw.columns = mstr_raw.columns.get_level_values(0)
    if isinstance(btc_raw.columns, pd.MultiIndex):
        btc_raw.columns = btc_raw.columns.get_level_values(0)

    # 統一將索引轉換為無時區的日期格式
    mstr_raw.index = pd.to_datetime(mstr_raw.index).tz_localize(None)
    btc_raw.index = pd.to_datetime(btc_raw.index).tz_localize(None)

    # 建立對齊表：以 MSTR 的交易日為基準
    df = pd.DataFrame(index=mstr_raw.index)
    df['MSTR_Price'] = mstr_raw['Close']
    
    # 透過 reindex 讓 BTC 價格對齊到 MSTR 的交易日
    df['BTC_Price'] = btc_raw['Close'].reindex(df.index, method='ffill') 
    
    # 剔除空值
    df = df.dropna()

    if not df.empty:
        # 計算指標
        df['NAV_per_share'] = (df['BTC_Price'] * BTC_HOLDINGS) / SHARES_OUTSTANDING
        df['Premium_Pct'] = ((df['MSTR_Price'] - df['NAV_per_share']) / df['NAV_per_share']) * 100

        # 指標顯示
        c1, c2, c3 = st.columns(3)
        c1.metric("MSTR Price", f"${df['MSTR_Price'].iloc[-1]:.2f}")
        c2.metric("BTC Price", f"${df['BTC_Price'].iloc[-1]:,.0f}")
        c3.metric("Premium %", f"{df['Premium_Pct'].iloc[-1]:.2f}%")

        # 繪圖
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Premium_Pct'], mode='lines', name='Premium %', line=dict(color='#00ffcc')))
        fig.update_layout(title="Historical Premium to NAV", template="plotly_dark")
        st.plotly_chart(fig, width='stretch')
        
        # AI 分析按鈕
        if st.button("Generate AI Insights"):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Analyze MSTR premium: {df['Premium_Pct'].tail(5).to_string()}. Reply in Chinese."
            st.info(model.generate_content(prompt).text)
    else:
        st.error("❌ 數據對齊失敗，請檢查 API 回傳內容。")
