import os
import hmac
import hashlib
import time
import requests
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

DELTA_API_KEY = os.environ.get("DELTA_API_KEY")
DELTA_API_SECRET = os.environ.get("DELTA_API_SECRET")
BASE_URL = os.environ.get("DELTA_BASE_URL", "https://api.demo.delta.exchange")

def generate_signature(method, endpoint, payload_str, timestamp):
    signature_data = method + timestamp + endpoint + payload_str
    return hmac.new(
        DELTA_API_SECRET.encode('utf-8'),
        signature_data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_ticker_price(product_symbol):
    try:
        url = f"{BASE_URL}/v2/tickers/{product_symbol}"
        response = requests.get(url)
        data = response.json()
        if data.get("success"):
            return float(data["result"]["close"])
    except Exception as e:
        print("Error fetching ticker price:", str(e))
    return None

def close_existing_positions(product_symbol):
    try:
        endpoint = "/v2/orders/close_all"
        timestamp = str(int(time.time()))
        payload = {"product_symbol": product_symbol}
        payload_str = json.dumps(payload)
        
        signature = generate_signature("POST", endpoint, payload_str, timestamp)
        headers = {
            "api-key": DELTA_API_KEY,
            "signature": signature,
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        res = requests.post(BASE_URL + endpoint, data=payload_str, headers=headers)
        print("Closed previous positions:", res.json())
        time.sleep(1)
    except Exception as e:
        print("Error closing existing positions:", str(e))

def send_delta_order(product_symbol, side, size):
    close_existing_positions(product_symbol)

    endpoint = "/v2/orders"
    timestamp = str(int(time.time()))
    
    current_price = get_ticker_price(product_symbol)
    
    payload = {
        "product_symbol": product_symbol,
        "size": int(size),
        "side": side,
        "order_type": "market_order"
    }

    if current_price:
        if side == "buy":
            stop_loss_price = round(current_price * 0.99, 1)
            take_profit_price = round(current_price * 1.02, 1)
        else:
            stop_loss_price = round(current_price * 1.01, 1)
            take_profit_price = round(current_price * 0.98, 1)

        payload["stop_trigger_method"] = "last_traded_price"
        payload["bracket_stop_loss_price"] = str(stop_loss_price)
        payload["bracket_take_profit_price"] = str(take_profit_price)

    payload_str = json.dumps(payload)
    signature = generate_signature("POST", endpoint, payload_str, timestamp)
    
    headers = {
        "api-key": DELTA_API_KEY,
        "signature": signature,
        "timestamp": timestamp,
        "Content-Type": "application/json"
    }
    
    response = requests.post(BASE_URL + endpoint, data=payload_str, headers=headers)
    return response.json()

@app.route('/', methods=['GET'])
def health_check():
    return "Delta Bot is Live & Running!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON data received"}), 400
        
        symbol = data.get("symbol", "BTCUSD")
        action = data.get("action")
        size = data.get("size", 1)
        
        if action in ["buy", "sell"]:
            res = send_delta_order(symbol, action, size)
            print("Delta Response:", res)
            return jsonify({"status": "success", "delta_response": res}), 200
        else:
            return jsonify({"status": "ignored", "message": "Invalid action"}), 400

    except Exception as e:
        print("Error processing webhook:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
