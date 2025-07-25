import requests
import time
import threading
import json
import os
from collections import deque, Counter
from flask import Flask, render_template, jsonify

app = Flask(__name__)
RESULTS_FILE = "results.json"
MAX_RESULTS = 1000
results = deque(maxlen=MAX_RESULTS)

# Load saved results
if os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, "r") as f:
        results.extend(json.load(f))

def fetch_results():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://draw.ar-lottery01.com/"
    }

    while True:
        try:
            ts = int(time.time() * 1000)
            response = requests.get(f"{url}?ts={ts}", headers=headers)
            response.raise_for_status()
            data = response.json()["data"]["list"]

            for item in reversed(data):
                if not any(r["issueNumber"] == item["issueNumber"] for r in results):
                    results.append({
                        "issueNumber": item["issueNumber"],
                        "number": int(item["number"]),
                        "color": item["color"]
                    })

            # Save results
            with open(RESULTS_FILE, "w") as f:
                json.dump(list(results), f, indent=2)

        except Exception as e:
            print("Error fetching results:", e)
        time.sleep(60)

def analyze_trends():
    if len(results) < 10:
        return "Loading..."

    last = results[-1]
    numbers = [r["number"] for r in results]
    colors = [c for r in results for c in r["color"].split(",")]

    # Trend Stats
    most_common_color = Counter(colors).most_common(1)[0][0]
    most_common_number = Counter(numbers).most_common(1)[0][0]

    # Big/Small prediction
    big_small = ["BIG" if n >= 5 else "SMALL" for n in numbers]
    prediction_size = Counter(big_small).most_common(1)[0][0]

    # Even/Odd prediction
    even_odd = ["EVEN" if n % 2 == 0 else "ODD" for n in numbers]
    prediction_parity = Counter(even_odd).most_common(1)[0][0]

    return {
        "predict_number": most_common_number,
        "predict_color": most_common_color,
        "predict_size": prediction_size,
        "predict_parity": prediction_parity,
        "last_issue": last["issueNumber"],
        "last_number": last["number"],
        "last_color": last["color"]
    }

@app.route("/")
def index():
    prediction = analyze_trends()
    return render_template("index.html", prediction=prediction, results=list(results)[-10:])

@app.route("/api")
def api():
    prediction = analyze_trends()
    return jsonify(prediction)

if __name__ == "__main__":
    threading.Thread(target=fetch_results, daemon=True).start()
    app.run(debug=False, host="0.0.0.0", port=5000)
