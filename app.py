import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. 配置與 AI 設置 ---
st.set_page_config(page_title="DAT.co 監測站", layout="wide")
# 替換成你的 API Key
genai.configure(api_key="AIzaSyBv6kKm_AzPQ1riyhPZMcbqzI5zSDnv96o")

# --- 2. 參數設置 (MicroStrategy) ---
# 這些數據通常來自最新的財報，對作業來說使用近似值即可
BTC_HOLDINGS = 252220  
SHARES_OUTSTANDING = 224440000 

st.title("🚀 Digital Asset Treasury (DAT.co) 監測平台")
st.markdown("本系統監控 **MicroStrategy (MSTR)** 的溢價率，作為比特幣市場情緒指標。")

# --- 3. 獲取數據 ---
# --- 3. 獲取數據 (更穩定的寫法) ---
@st.cache_data(ttl=600) # 縮短快取時間，方便重試
def fetch_financial_data():
    try:
        mstr_obj = yf.Ticker("MSTR")
        btc_obj = yf.Ticker("BTC-USD")
        
        # 抓取數據並處理多層索引問題
        mstr = mstr_obj.history(period="1y")
        btc = btc_obj.history(period="1y")
        
        return mstr, btc
    except Exception as e:
        st.error(f"API 請求失敗: {e}")
        return pd.DataFrame(), pd.DataFrame()

mstr_raw, btc_raw = fetch_financial_data()

# --- 檢查數據是否有效 ---
if mstr_raw.empty or btc_raw.empty:
    st.warning("⚠️ 目前 Yahoo Finance API 流量受限，請稍候 1-2 分鐘後重新整理網頁。")
    st.info("這通常是因為雲端伺服器 (Streamlit Cloud) 的 IP 被暫時限制，不影響程式邏輯。")
else:
    # 數據對齊處理
    df = pd.DataFrame()
    df['MSTR_Price'] = mstr_raw['Close']
    df['BTC_Price'] = btc_raw['Close']
    df = df.dropna()

    if not df.empty:
        # 計算指標
        df['NAV_per_share'] = (df['BTC_Price'] * BTC_HOLDINGS) / SHARES_OUTSTANDING
        df['Premium_Pct'] = ((df['MSTR_Price'] - df['NAV_per_share']) / df['NAV_per_share']) * 100

        # --- 4. UI 視覺化 ---
        c1, c2, c3 = st.columns(3)
        c1.metric("MSTR Price", f"${df['MSTR_Price'].iloc[-1]:.2f}")
        c2.metric("BTC Price", f"${df['BTC_Price'].iloc[-1]:,.0f}")
        c3.metric("Current Premium", f"{df['Premium_Pct'].iloc[-1]:.2f}%")

        # 繪圖
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Premium_Pct'], mode='lines', name='Premium %', line=dict(color='#00ffcc')))
        fig.update_layout(title="MSTR Premium to NAV Tracker", template="plotly_dark")
        st.plotly_chart(fig, width='stretch')
        
        # ... (後續 AI 部分保持不變)
    else:
        st.error("數據對齊後為空，請檢查日期範圍。")

try:
    mstr_raw, btc_raw = fetch_financial_data()

    # 數據處理與對齊
    df = pd.DataFrame()
    df['MSTR_Price'] = mstr_raw['Close']
    df['BTC_Price'] = btc_raw['Close']
    df = df.dropna()

    # 計算指標：NAV (Net Asset Value) 與 Premium (溢價)
    df['NAV_per_share'] = (df['BTC_Price'] * BTC_HOLDINGS) / SHARES_OUTSTANDING
    df['Premium_Pct'] = ((df['MSTR_Price'] - df['NAV_per_share']) / df['NAV_per_share']) * 100

    # --- 4. UI 視覺化 ---
    # 顯示數據指標卡片
    c1, c2, c3 = st.columns(3)
    c1.metric("MSTR 現價", f"${df['MSTR_Price'].iloc[-1]:.2f}")
    c2.metric("BTC 現價", f"${df['BTC_Price'].iloc[-1]:,.0f}")
    c3.metric("當前溢價率", f"{df['Premium_Pct'].iloc[-1]:.2f}%")

    # 繪製溢價率走勢圖
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Premium_Pct'], mode='lines', name='Premium %', line=dict(color='#00ffcc')))
    fig.update_layout(
        title="MSTR 歷史溢價率走勢 (Premium to NAV)",
        xaxis_title="日期",
        yaxis_title="溢價率 (%)",
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. AI 洞察 (加分項) ---
    st.divider()
    st.subheader("🤖 AI 數據解讀")
    if st.button("生成分析報告"):
        with st.spinner("Gemini 正在思考中..."):
            # 修改後的程式碼
            model = genai.GenerativeModel('gemini-pro')
            # 準備數據摘要給 AI
            summary_data = df[['MSTR_Price', 'BTC_Price', 'Premium_Pct']].tail(10).to_string()
            prompt = f"""
            你是一位專業的加密貨幣分析師。以下是 MicroStrategy (MSTR) 最近 10 天的數據：
            {summary_data}
            
            請針對「溢價率」的趨勢給出簡短分析，並說明這對比特幣投資者意味著什麼（是過熱還是低估？）。
            請用中文回答。
            """
            response = model.generate_content(prompt)
            st.info(response.text)

except Exception as e:
    st.error(f"數據加載出錯: {e}")
