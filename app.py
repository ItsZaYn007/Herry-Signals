import requests
import time
from collections import Counter, deque
from typing import List, Dict
import json
import os
from flask import Flask, render_template
import threading

# --- Flask Setup with Safe Path for JSON File ---
app = Flask(__name__, instance_relative_config=True)
os.makedirs(app.instance_path, exist_ok=True)
HISTORY_FILE = os.path.join(app.instance_path, "results_history.json")
MAX_HISTORY = 5000

# --- State ---
total_bets = 0
total_wins = 0
total_losses = 0
win_streak = 0
loss_streak = 0
results_history = deque(maxlen=MAX_HISTORY)
latest_prediction = None
latest_validation = None
last_result_id = None

# --- Helper Functions ---
def load_history():
    """Load historical results from file."""
    global results_history
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                results_history.extend(data[-MAX_HISTORY:])
        except Exception as e:
            print(f"Failed to load history: {e}")

def save_history():
    """Save historical results to file."""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(list(results_history), f)
    except Exception as e:
        print(f"Failed to save history: {e}")

def get_last_results(n=10) -> List[Dict]:
    """Fetch the latest 10 results from the API with timeout."""
    try:
        response = requests.get(
            f"https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?ts={int(time.time() * 1000)}",
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile)",
                "Referer": "https://draw.ar-lottery01.com/",
                "Accept": "application/json"
            },
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]["list"][:n]
    except Exception as e:
        print(f"Failed to fetch results: {e}")
        return list(results_history) if results_history else []

def number_type(n: int) -> str:
    return "Small" if 0 <= n <= 4 else "Big"

# --- Trend Extraction ---
def extract_type_trend(results: List[Dict]) -> List[str]:
    return [number_type(int(res["number"])) for res in results]

def extract_color_trend(results: List[Dict]) -> List[str]:
    return [res["color"] for res in results]

# --- Trend Detection Formulas ---
def detect_color_cycle(colors: List[str]) -> str:
    if len(colors) < 3: return ""
    last3 = colors[-3:]
    if last3 == ["red", "green", "green"]: return "Small"
    if last3 == ["green", "green", "green"]: return "Big"
    return ""

def detect_alternation(big_small: List[str]) -> str:
    if len(big_small) < 4: return ""
    if big_small[-3:] == ["Big", "Small", "Big"]: return "Small"
    if big_small[-3:] == ["Small", "Big", "Small"]: return "Big"
    return ""

def modulus_issue_hint(issue_number: str) -> str:
    try:
        last_digit = int(issue_number[-1])
        return "Big" if last_digit % 2 == 0 else "Small"
    except:
        return ""

def recent_gap_analysis(numbers: List[int]) -> str:
    if len(numbers) < 2: return ""
    gaps = [abs(numbers[i] - numbers[i - 1]) for i in range(1, len(numbers))]
    avg_gap = sum(gaps) / len(gaps)
    return "Big" if avg_gap >= 5 else "Small"

# --- Prediction Logic ---
def predict_next(results: List[Dict]) -> Dict:
    if not results: return {}
    numbers = [int(res["number"]) for res in results]
    types = extract_type_trend(results)
    colors = extract_color_trend(results)
    issue_number = results[0]["issueNumber"]

    prediction_scores = Counter()
    hints = []

    color_hint = detect_color_cycle(colors)
    if color_hint:
        prediction_scores[color_hint] += 2
        hints.append(f"Color Cycle: {color_hint}")

    alt_hint = detect_alternation(types)
    if alt_hint:
        prediction_scores[alt_hint] += 1
        hints.append(f"Alternation: {alt_hint}")

    mod_hint = modulus_issue_hint(issue_number)
    if mod_hint:
        prediction_scores[mod_hint] += 2
        hints.append(f"Modulus: {mod_hint}")

    gap_hint = recent_gap_analysis(numbers)
    if gap_hint:
        prediction_scores[gap_hint] += 1
        hints.append(f"Gap Analysis: {gap_hint}")

    predicted = prediction_scores.most_common(1)
    signal = predicted[0][0] if predicted else "Big"

    return {
        "period": str(int(issue_number) + 1),
        "signal": signal,
        "hints": hints
    }

# --- Update History ---
def update_history():
    global results_history
    new_results = get_last_results(10)
    if new_results:
        current_ids = {res["issueNumber"] for res in results_history}
        for res in reversed(new_results):
            if res["issueNumber"] not in current_ids:
                results_history.appendleft(res)
        save_history()
    return list(results_history)

# --- Validate Prediction ---
def validate_prediction(prediction: Dict, latest_result: Dict) -> Dict:
    global total_bets, total_wins, total_losses, win_streak, loss_streak
    if not prediction or not latest_result: return {}
    result_number = int(latest_result["number"])
    result_type = number_type(result_number)
    return {
        "signal": prediction["signal"],
        "result": "✅ WIN" if prediction["signal"] == result_type else "❌ LOSS",
        "winning_number": result_number
    }

# --- Background Thread ---
def background_task():
    global latest_prediction, latest_validation, last_result_id
    print("Starting background task...")
    load_history()
    if results_history:
        latest_prediction = predict_next(list(results_history))
    while True:
        try:
            results = update_history()
            if not results:
                time.sleep(1)
                continue
            current_result_id = results[0]["issueNumber"]
            if last_result_id and current_result_id != last_result_id:
                if latest_prediction:
                    latest_validation = validate_prediction(latest_prediction, results[0])
                latest_prediction = predict_next(results)
            last_result_id = current_result_id
            time.sleep(1)
        except Exception as e:
            print(f"Background task error: {e}")
            time.sleep(1)

# --- Start Background Thread ---
threading.Thread(target=background_task, daemon=True).start()

# --- Flask Route ---
@app.route('/')
def home():
    recent_results = list(results_history)[:10]
    trends = {
        "type_trend": [number_type(int(res["number"])) for res in recent_results],
        "color_trend": [res["color"] for res in recent_results]
    }
    return render_template('index.html',
                           prediction=latest_prediction,
                           validation=latest_validation,
                           trends=trends,
                           results_history=recent_results)

# --- Run App ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
