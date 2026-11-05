import os
import time
import logging
import pyotp
import pandas as pd
import numpy as np
import requests
from SmartApi import SmartConnect
from datetime import datetime

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- API & Telegram Configurations ---
API_KEY = "iemEXsyV"
CLIENT_ID = "B253694"
PASSWORD = "7172"
TOTP_SECRET = "D4YNATHBA3VFIW5C7YUQPJNVIE"

TELEGRAM_BOT_TOKEN = "9026439091:AAFIKpcddjPnFfx-k-Wc8GUSSdHvgOd0w5k"
TELEGRAM_CHAT_ID = "1486399523"

# --- Paper Trade Active State ---
active_paper_trade = None

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
            logging.error("Telegram Error: " + response.text)
    except Exception as e:
        logging.error("Failed to send Telegram alert: " + str(e))

# --- Indicator Calculations (MA 60 & RSI Stochastic 75/35) ---
def calculate_indicators(df):
    df['MA_60'] = df['close'].rolling(window=60).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    r_low = rsi.rolling(window=14).min()
    r_high = rsi.rolling(window=14).max()
    df['Stoch_RSI'] = (rsi - r_low) / (r_high - r_low) * 100
    
    return df

# --- Strategy Logic (Only Options: CE BUY / PE BUY) ---
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
    
    if prev_close <= prev['MA_60'] and close > ma_60 and prev_stoch <= 35 and stoch > 35:
        signal = "ATM CE BUY"
        sl = prev['low']
        risk = entry_price - sl
        target = entry_price + risk
        
    elif close > ma_60 and prev['low'] <= prev['MA_60'] and close > prev_close and stoch > prev_stoch and stoch <= 45:
        signal = "ATM CE BUY (Support)"
        sl = prev['low']
        risk = entry_price - sl
        target = entry_price + risk

    elif prev_close >= prev['MA_60'] and close < ma_60 and prev_stoch >= 75 and stoch < 75:
        signal = "ATM PE BUY"
        sl = prev['high']
        risk = sl - entry_price
        target = entry_price - risk
        
    elif close < ma_60 and prev['high'] >= prev['MA_60'] and close < prev_close and stoch < prev_stoch and stoch >= 55:
        signal = "ATM PE BUY (Resistance)"
        sl = prev['high']
        risk = sl - entry_price
        target = entry_price - risk

    if signal:
        return {
            "symbol": symbol,
            "signal": signal,
            "price": entry_price,
            "sl": sl,
            "target": target
        }
    return None

# --- Main Execution Loop with Paper Trading ---
def run_algo():
    global active_paper_trade
    logging.info("Initializing Angel One SmartAPI connection for Data Feeds...")
    try:
        obj = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = obj.generateSession(CLIENT_ID, PASSWORD, totp)
        
        if not data or 'status' not in data or not data['status']:
            logging.error("SmartAPI Login Failed: " + str(data))
            send_telegram_alert("⚠️ *Angel One Login Failed!* कृपया क्रेडेन्शियल्स तपासा.")
            return
            
        logging.info("SmartAPI Login Successful!")
        send_telegram_alert("🚀 *Community Options Paper Trading Bot Activated!*\nCapital: ₹20,000 (Virtual) | Strategy: MA 60 + RSI Stoch (75/35)")
        
    except Exception as e:
        logging.error("Connection error: " + str(e))
        send_telegram_alert("⚠️ *Connection Error:* " + str(e))
        return

    symbols = [
        {"name": "CRUDEOIL", "token": "260373"}, 
        {"name": "SILVERMIC", "token": "260384"}
    ]
    
    while True:
        try:
            for item in symbols:
                symbol_name = item["name"]
                token = item["token"]
                
                to_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                from_date = datetime.now().strftime("%Y-%m-%d 09:00")
                
                historicParam = {
                    "exchange": "MCX",
                    "symboltoken": token,
                    "interval": "FIVE_MINUTE",
                    "fromdate": from_date,
                    "todate": to_date
                }
                
                response = obj.getCandleData(historicParam)
                if response and 'data' in response and response['data']:
                    candles = response['data']
                    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['close'] = df['close'].astype(float)
                    df['high'] = df['high'].astype(float)
                    df['low'] = df['low'].astype(float)
                    
                    df = calculate_indicators(df)
                    
                    # Check active paper trade target/stoploss if any exists
                    current_price = df.iloc[-1]['close']
                    if active_paper_trade and active_paper_trade['symbol'] == symbol_name:
                        if "CE" in active_paper_trade['signal']:
                            if current_price >= active_paper_trade['target']:
                                send_telegram_alert(f"🎯 *PAPER TRADE TARGET HIT!* \nSymbol: {symbol_name}\nExit Price: {current_price}")
                                active_paper_trade = None
                            elif current_price <= active_paper_trade['sl']:
                                send_telegram_alert(f"🛑 *PAPER TRADE STOP LOSS HIT!* \nSymbol: {symbol_name}\nExit Price: {current_price}")
                                active_paper_trade = None
                        elif "PE" in active_paper_trade['signal']:
                            if current_price <= active_paper_trade['target']:
                                send_telegram_alert(f"🎯 *PAPER TRADE TARGET HIT!* \nSymbol: {symbol_name}\nExit Price: {current_price}")
                                active_paper_trade = None
                            elif current_price >= active_paper_trade['sl']:
                                send_telegram_alert(f"🛑 *PAPER TRADE STOP LOSS HIT!* \nSymbol: {symbol_name}\nExit Price: {current_price}")
                                active_paper_trade = None

                    # Look for new signal only if no trade is currently active
                    if not active_paper_trade:
                        result = check_strategy_signals(df, symbol_name)
                        if result:
                            active_paper_trade = result
                            msg = (
                                f"📝 *VIRTUAL PAPER TRADE EXECUTED* 📝\n\n"
                                f"📌 **Symbol:** {result['symbol']}\n"
                                f"⚡ **Signal:** {result['signal']}\n"
                                f"💰 **Entry Price:** {result['price']}\n"
                                f"🛑 **Stop Loss (SL):** {result['sl']}\n"
                                f"🎯 **Target (1:1):** {result['target']}\n"
                                f"💵 **Virtual Capital:** ₹20,000\n"
                                f"⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                            send_telegram_alert(msg)
                
            time.sleep(300)
            
        except Exception as e:
            logging.error("Error in execution loop: " + str(e))
            time.sleep(60)

if __name__ == "__main__":
    run_algo()
    
