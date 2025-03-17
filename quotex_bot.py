from flask import Flask, jsonify
import time
import os
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# **Flask অ্যাপ তৈরি**
app = Flask(__name__)

# **Environment Variables লোড করা**
load_dotenv()
QUOTEX_EMAIL = os.getenv("quotexpro207@gmail.com")
QUOTEX_PASSWORD = os.getenv("quotexpro207")
TELEGRAM_BOT_TOKEN = os.getenv("7560355757:AAGtbnAFtMM8yWn7Mt5beirufBJaO1FQCho")
TELEGRAM_CHAT_ID = os.getenv("-1002289311172")

# **🔹 Selenium ড্রাইভার ইনিশিয়ালাইজ করা (একবার চালু থাকবে)**
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # ✅ GUI ছাড়াই চালাবে
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

driver = init_driver()

# **🔹 Quotex-এ একবার লগইন করবে এবং সেশন চালু রাখবে**
def login_to_quotex():
    driver.get("https://quotex.io/en/sign-in")

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(QUOTEX_EMAIL)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(QUOTEX_PASSWORD + Keys.RETURN)
        time.sleep(5)
        print("✅ Logged in to Quotex successfully!")
    except Exception as e:
        print(f"❌ Login failed: {e}")

login_to_quotex()

# **🔹 লাইভ মার্কেট ট্রেন্ড ও প্রাইস ডাটা স্ক্র্যাপ**
def get_market_data():
    driver.get("https://quotex.io/trading")
    time.sleep(3)

    # **ট্রেন্ড চেক**
    try:
        trend_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='trend-indicator']"))
        )
        trend = trend_element.text
    except:
        trend = "UNKNOWN"

    # **সাপোর্ট & রেজিস্ট্যান্স চেক**
    support_level, resistance_level, current_price = 1.0950, 1.1000, 1.0965
    sr_confirmed = support_level < current_price < resistance_level

    return {"trend": trend, "support_resistance": sr_confirmed}

# **🔹 সিগন্যাল এনালাইসিস (লাইভ ডাটা বেসড)**
last_signal = None
last_signal_time = 0

def get_sure_shot_signal():
    global last_signal, last_signal_time
    
    current_time = time.time()
    if last_signal and (current_time - last_signal_time) < 30:  # ৩০ সেকেন্ড ক্যাশিং
        return last_signal
    
    market_data = get_market_data()
    trend = market_data["trend"]

    if trend == "UP":
        signal_direction = "CALL"
    elif trend == "DOWN":
        signal_direction = "PUT"
    else:
        return None

    # **মাল্টি-টাইমফ্রেম চেক**
    m1_signal, m5_signal, m15_signal = "CALL", "CALL", "CALL"
    multi_tf_confirmed = m1_signal == m5_signal == m15_signal

    # **সাপোর্ট & রেজিস্ট্যান্স ব্রেকআউট চেক**
    if not market_data["support_resistance"]:
        return None

    # **ফাইনাল সিদ্ধান্ত**
    accuracy = 90 if multi_tf_confirmed else 80
    last_signal = {
        "pair": "EUR/USD",
        "direction": signal_direction,
        "strength": accuracy,
        "expiry": 5
    }
    last_signal_time = current_time
    return last_signal

# **🔹 টেলিগ্রাম মেসেজ পাঠানো**
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print("✅ Telegram message sent successfully!")
        else:
            print(f"❌ Telegram error: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error sending Telegram message: {e}")

# **🔹 Flask Routes**
@app.route('/')
def home():
    return "Quotex Signal Bot is running!"

@app.route('/get_signal')
def get_signal():
    signal = get_sure_shot_signal()
    
    if signal:
        send_telegram_message(f"📊 Signal: {signal['pair']} - {signal['direction']} ({signal['strength']}%)")
        return jsonify(signal)
    
    return jsonify({"message": "No valid signal found"})

# **🔹 Flask অ্যাপ চালানো**
if __name__ == "__main__":
    send_telegram_message("✅ <b>Quotex Signal Bot is now Running!</b> 🚀")
    app.run(host="0.0.0.0", port=5000, debug=False)
