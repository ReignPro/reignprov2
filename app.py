from flask import Flask, render_template, request, jsonify
import glob
import json
import os

app = Flask(__name__)
DATA_FOLDER = "parsed_results"  # Folder with JSON trade files

def load_all_trades():
    files = glob.glob(os.path.join(DATA_FOLDER, "*.json"))
    all_trades = []
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_trades.extend(data)
    return all_trades

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/trades")
def api_trades():
    all_trades = load_all_trades()

    trader = request.args.get("trader")
    symbol = request.args.get("symbol")
    direction = request.args.get("direction")
    missing_sl = request.args.get("missing_sl")

    filtered = all_trades
    if trader:
        filtered = [t for t in filtered if t.get("trader","").lower() == trader.lower()]
    if symbol:
        filtered = [t for t in filtered if t.get("symbol","").lower() == symbol.lower()]
    if direction:
        filtered = [t for t in filtered if t.get("side","").lower() == direction.lower()]
    if missing_sl == "true":
        filtered = [t for t in filtered if not t.get("sl")]

    # Pagination parameters
    start = int(request.args.get("start", 0))
    length = int(request.args.get("length", 50))

    data_page = filtered[start:start+length]

    return jsonify({
        "recordsTotal": len(filtered),
        "recordsFiltered": len(filtered),
        "data": data_page
    })

if __name__ == "__main__":
    app.run(debug=True)
