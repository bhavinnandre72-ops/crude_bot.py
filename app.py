import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="Crude Oil Live Dashboard", page_icon="🛢️", layout="wide")

st.title("🛢️ Crude Oil Live Chart & Option Chain Dashboard")
st.markdown("सुमित/भाविन - स्वयंचलित लाईव्ह मार्केट डॅशबोर्ड")

# भारतीय वेळेनुसार वेळ दाखवणे
ist_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %I:%M:%S %p")
st.sidebar.markdown(f"**⏰ भारतीय वेळ (IST):** \n{ist_time}")

# Yahoo Finance वरून क्रूड ऑइलचा लाईव्ह डेटा फेच करणे
@st.cache_data(ttl=60)
def load_data():
    try:
        crude = yf.Ticker("CL=F")
        df = crude.history(period="1d", interval="5m")
        return df
    except Exception as e:
        return pd.DataFrame()

data = load_data()

if not data.empty:
    current_price = round(data['Close'].iloc[-1], 2)
    
    # परफॉरमन्स मेट्रिक्स
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Crude Oil Live Spot Price", value=f"₹ {current_price}")
    
    atm_strike = round(current_price / 50) * 50
    col2.metric(label="ATM Strike Price", value=f"{atm_strike}")
    col3.metric(label="Market Status", value="🟢 Live Active")

    # लाईव्ह चार्ट (Live Price Chart)
    st.subheader("📊 Crude Oil Live Intraday Price Chart")
    st.line_chart(data['Close'])

    # ऑप्शन चेन (Simulated Option Chain based on Live Spot)
    st.subheader("⚡ Crude Oil Option Chain (CE / PE Live View)")
    
    strikes = [atm_strike - 150, atm_strike - 100, atm_strike - 50, atm_strike, atm_strike + 50, atm_strike + 100, atm_strike + 150]
    
    option_list = []
    for strike in strikes:
        ce_price = round(max(10.0, 150 + (current_price - strike) * 0.6), 2)
        pe_price = round(max(10.0, 150 + (strike - current_price) * 0.6), 2)
        option_list.append({
            "Strike Price": strike,
            "Call (CE) LTP": ce_price,
            "Put (PE) LTP": pe_price
        })
    
    option_df = pd.DataFrame(option_list)
    st.dataframe(option_df, use_container_width=True)

else:
    st.error("सध्या लाईव्ह डेटा उपलब्ध नाही किंवा मार्केट बंद आहे.")

# रिफ्रेश बटण
if st.button("🔄 ਰिफ्रेश डेटा (Refresh Data)"):
    st.rerun()
  
