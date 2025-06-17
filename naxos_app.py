from flask import Flask, request, jsonify, render_template, redirect
import sqlite3
import uuid
import time
import threading
import os
import subprocess
import requests
import base64

app = Flask(__name__)

DB_PATH = 'subscriptions.db'
CHECK_INTERVAL = 30  # seconds

# ---------------------- Daraja API Configuration ----------------------
DARAJA_CONSUMER_KEY = 'your_consumer_key_here'
DARAJA_CONSUMER_SECRET = 'your_consumer_secret_here'
DARAJA_SHORTCODE = '174379'  # Example shortcode for Equity BDCD
DARAJA_PASSKEY = 'your_passkey_here'
CALLBACK_URL = 'https://example.com/callback'

# ---------------------- Database Setup ----------------------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                ip TEXT,
                phone TEXT,
                start_time INTEGER,
                duration INTEGER,
                active INTEGER
            )
        ''')

init_db()

# ---------------------- Network Control ----------------------
def allow_ip(ip):
    subprocess.call(["sudo", "iptables", "-I", "FORWARD", "-s", ip, "-j", "ACCEPT"])

def block_ip(ip):
    subprocess.call(["sudo", "iptables", "-D", "FORWARD", "-s", ip, "-j", "ACCEPT"])

# ---------------------- Background Timer ----------------------
def check_subscriptions():
    while True:
        now = int(time.time())
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("SELECT id, ip, start_time, duration FROM subscriptions WHERE active=1").fetchall()
            for id_, ip, start, dur in rows:
                if now > (start + dur):
                    block_ip(ip)
                    conn.execute("UPDATE subscriptions SET active=0 WHERE id=?", (id_,))
        time.sleep(CHECK_INTERVAL)

threading.Thread(target=check_subscriptions, daemon=True).start()

# ---------------------- Daraja API Helpers ----------------------
def get_access_token():
    auth = base64.b64encode(f"{DARAJA_CONSUMER_KEY}:{DARAJA_CONSUMER_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    response = requests.get("https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials", headers=headers)
    return response.json().get("access_token")

def initiate_stk_push(phone, amount):
    access_token = get_access_token()
    timestamp = time.strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{DARAJA_SHORTCODE}{DARAJA_PASSKEY}{timestamp}".encode()).decode()

    payload = {
        "BusinessShortCode": DARAJA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": DARAJA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "083982793",
        "TransactionDesc": "WiFi Subscription"
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    response = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", json=payload, headers=headers)
    return response.json()

# ---------------------- Flask Routes ----------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate_204')
def g204():
    return redirect("http://10.50.0.1:5000")

@app.route('/chat')
def chat():
    return redirect("http://10.50.0.1:5000")

@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.json
    duration = int(data['duration']) * 60  # convert to seconds
    phone = data['phone']
    ip = request.remote_addr
    sub_id = str(uuid.uuid4())
    start = int(time.time())

    # Optional: amount could be set depending on duration
    amount = 10 if duration == 60 else 15 if duration == 180 else 20 if duration == 780 else 25
    stk_response = initiate_stk_push(phone, amount)

    if stk_response.get("ResponseCode") != "0":
        return jsonify({"success": False, "message": "Payment initiation failed"})

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO subscriptions (id, ip, phone, start_time, duration, active) VALUES (?, ?, ?, ?, ?, 1)",
                     (sub_id, ip, phone, start, duration))

    allow_ip(ip)

    return jsonify({"success": True, "id": sub_id})

@app.route('/resume', methods=['POST'])
def resume():
    data = request.json
    sub_id = data['id']
    ip = request.remote_addr

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT start_time, duration, active FROM subscriptions WHERE id=?", (sub_id,)).fetchone()
        if not row:
            return jsonify({"success": False, "message": "Invalid ID"})

        start, duration, active = row
        now = int(time.time())

        if now > (start + duration):
            return jsonify({"success": False, "message": "Expired"})

        conn.execute("UPDATE subscriptions SET ip=?, active=1 WHERE id=?", (ip, sub_id))
        allow_ip(ip)
        remaining = (start + duration) - now

    return jsonify({"success": True, "message": f"Access restored. {remaining//60} min remaining."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)