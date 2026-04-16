import os
import sys
import json

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Drawer")
os.makedirs(APP_DIR, exist_ok=True)

SESSION_FILE = os.path.join(APP_DIR, "session.json")

def save_session(data, path=None):
    if path is None:
        path = SESSION_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_session(path=None):
    if path is None:
        path = SESSION_FILE
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
