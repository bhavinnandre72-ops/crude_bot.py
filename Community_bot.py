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

# --- Updated Strategy Logic with 3-Candle Flexibility ---
def check_strategy_signals(df, symbol):
    if len(df) < 70:
        return None
    
    current = df.iloc[-1]
    entry_price = current['close']
    
    signal = None
    sl = 0
    target = 0
    
    # गेल्या ३ कॅण्डल्सच्या डेटावरून क्रॉसओव्हर तपासणे (Tolerance of last 3 candles)
    recent_df = df.iloc[-4:]
    
    # CE BUY Condition: मागील ३ कॅण्डल्समध्ये MA 60 क्रॉस केला असला किंवा Stoch 35 च्या वर गेला असला तरी चालेल
    ce_crossover = any((recent_df['close'].shift(1) <= recent_df['MA_60'].shift(1)) & (recent_df['close'] > recent_df['MA_60']))
    stoch_ce_cond = any((recent_df['Stoch_RSI'].shift(1) <=
    
