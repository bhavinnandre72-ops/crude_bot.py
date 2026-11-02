import os
import time
import logging
import pandas as pd
import numpy as np
import requests
from SmartApi import SmartConnect
from datetime import datetime

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- API & Telegram Configurations ---
# तुमच्या क्रेडेन्शियल्सनुसार येथे माहिती भरा किंवा Environment Variables वापरा
API_KEY = os.getenv("SMARTAPI_KEY", "iemEXsyV")
CLIENT_ID = os.getenv("CLIENT_ID", "B253694")
PASSWORD = os.getenv("PASSWORD", "7172")
TOTP_SECRET = "D4YNATHBA3VFIW5C7YUQPJNVIE"

TELEGRAM_BOT_TOKEN = "9026439091:AAFIKpcddjPnFfx-k-Wc8GUSSdHvgOd0w5k"
TELEGRAM_CHAT_ID = "1486399523"

# --- Telegram Alert Function ---
def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logging.error(f"Telegram Error: {response.text}")
    except Exception as e:
        logging.error(f"Failed to send Telegram alert: {e}")

# --- Indicator Calculations ---
def calculate_indicators(df):
    # 1. Moving Average 60
    df['MA_60'] = df['close'].rolling(window=60).mean()
    
    # 2. RSI Stochastic (75/35) Calculation
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Stochastic of RSI (14 period)
    r_low = rsi.rolling(window=14).min()
    r_high = rsi.rolling(window=14).max()
    df['Stoch_RSI'] = (rsi - r_low) / (r_high - r_low) * 100
    
    return df

# --- Strategy Logic ---
def check_strategy_signals(df, symbol):
    if len(df) < 65:
        return None
    
    current = df.iloc[-1]
    prev = df.iloc[-2]
    
    ma_60 = current['MA_60']
    close = current['close']
    prev_close = prev['close']
    stoch = current['Stoch_RSI']
    prev_stoch = prev['Stoch_RSI']
    
    signal = None
    entry_price = close
    sl = 0
    target = 0
    
    # --- CE BUY / FUTURE BUY CONDITIONS ---
    # Condition 1: MA 60 Crossover from below + Stoch crossing 35 from below
    if prev_close <= prev['MA_60'] and close > ma_60 and prev_stoch <= 35 and stoch > 35:
        signal = "CE_BUY"
        sl = prev['low']
        risk = entry_price - sl
        target = entry_price + risk  # 1:1 Target
        
    # Condition 2: Support at MA 60 (Green candle taking support) + Stoch taking support near 35
    elif close > ma_60 and prev['low'] <= prev['MA_60'] and close > prev_close and stoch > prev_stoch and stoch <= 45:
        signal = "CE_BUY"
        sl = prev['low']
        risk = entry_price - sl
        target = entry_price + risk  # 1:1 Target

    # --- PE BUY / FUTURE SELL CONDITIONS ---
    # Condition 3: MA 60 Breakdown from above + Stoch crossing 75 from above
    elif prev_close >= prev['MA_60'] and close < ma_60 and prev_stoch >= 75 and stoch < 75:
        signal = "PE_BUY"
        sl = prev['high']
        risk = sl - entry_price
        target = entry_price - risk  # 1:1 Target
        
    # Condition 4: Resistance at MA 60 (Red candle taking resistance) + Stoch taking resistance near 75
    elif close < ma_60 and prev['high'] >= prev['MA_60'] and close < prev_close and stoch < prev_stoch and stoch >= 55:
        signal = "PE_BUY"
        sl = prev['high']
        risk = sl - entry_price
        target = entry_price - risk  # 1:1 Target

    if signal:
        return {
            "symbol": symbol,
            "signal": signal,
            "price": entry_price,
            "sl": sl,
            "target": target
        }
    return None

# --- Main Execution Loop for Paper Trading ---
def run_algo():
    logging.info("Initializing Angel One SmartAPI connection...")
    try:
        obj = SmartConnect(api_key=API_KEY)
        data = obj.generateSession(CLIENT_ID, PASSWORD)
        if not data['status']:
            logging.error("SmartAPI Login Failed: " + str(data))
            return
        logging.info("SmartAPI Login Successful!")
    except Exception as e:
        logging.error(f"Connection error: {e}")
        return

    # तुमच्या वॉचलिस्ट मधील कमोडिटी सिम्बॉल (उदा. Crude Oil / Silver)
    symbols = ["CRUDEOIL", "SILVERMIC"] 
    
    while True:
        try:
            for symbol in symbols:
                # येथे तुम्ही लाईव कॅण्डल डेटा फेच करू शकता (उदा. 5 मिनिटे टाइमफ्रेम)
                # उदाहरणासाठी डमी डेटा फ्रेम स्ट्रक्चर वापरले आहे, प्रत्यक्ष API कॉल्स द्वारे OHLC डेटा टाकावा
                
                # TODO: Replace with actual SmartAPI historical data fetch call for 5 min timeframe
                # historicalData = obj.getCandleData({...})
                
                pass
                
            time.sleep(300) # दर ५ मिनिटांनी तपासेल
        except Exception as e:
            logging.error(f-`Error in execution loop: {e}`)
            time.sleep(60)

if __name__ == "__main__":
    send_telegram_alert("🚀 *Bhavin Trading Bot Initialized Successfully!*\nCapital: ₹20,000 | Strategy: MA 60 + RSI Stochastic Active.")
    # run_algo() # अनकमेंट करा जेव्हा लाई लाइव्ह रन करायचे असेल
