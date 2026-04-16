import os
import sys
import json

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Drawer")
os.makedirs(APP_DIR, exist_ok=True)

SESSION_FILE = os.path.join(APP_DIR, "session.json")

# One-time migration: copy session.json from old exe-adjacent location
def _migrate_old_session():
    if os.path.isfile(SESSION_FILE):
        return
    if getattr(sys, "frozen", False):
        old_dir = os.path.dirname(sys.executable)
    else:
        old_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    old_file = os.path.join(old_dir, "session.json")
    if os.path.isfile(old_file):
        import shutil
        shutil.copy2(old_file, SESSION_FILE)

_migrate_old_session()

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
