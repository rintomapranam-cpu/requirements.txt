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
BASE_URL = "https://api.delta.exchange"

def generate_signature(method, endpoint, payload_str, timestamp):
    signature_data = method + timestamp + endpoint + payload_str
    return hmac.new(
        DELTA_API_SECRET.encode('utf-8'),
        signature_data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def send_delta_order(product_symbol, side, size):
    endpoint = "/v2/orders"
    timestamp = str(int(time.time()))
    
    payload = {
        "product_symbol": product_symbol,
        "size": size,
        "side": side,
        "order_type": "market_order"
    }
    
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

if __name__ == 'main':
    app.run(host='0.0.0.0', port=5000)
