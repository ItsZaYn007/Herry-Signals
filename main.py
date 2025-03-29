from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import requests
import random
import numpy as np
from collections import deque
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_URL = os.getenv("API_URL", "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json")

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

winning_memory = deque(maxlen=20)

def fetch_game_history():
    try:
        response = requests.get(API_URL, timeout=5)
        if response.status_code != 200:
            return []
        data = response.json().get("data", {}).get("list", [])
        if not isinstance(data, list):
            return []
        return data
    except:
        return []

def generate_prediction():
    history = fetch_game_history()
    if len(history) < 10:
        return None  

    latest_period = int(history[0]["issueNumber"]) + 1
    numbers = [int(game["number"]) for game in history[:10]]
    mean_value = int(np.mean(numbers))  

    available_numbers = list(set(range(10)) - set(winning_memory))
    if not available_numbers:
        available_numbers = list(range(10))

    predicted_numbers = random.sample(available_numbers, 2)
    signal = "BIG" if mean_value > 5 else "SMALL"

    return {"period": latest_period, "signal": signal, "number": predicted_numbers}

@app.get("/")
def home(request: Request):
    prediction = generate_prediction()
    return templates.TemplateResponse("index.html", {"request": request, "prediction": prediction})