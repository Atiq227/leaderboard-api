from flask import Flask, request, jsonify
import json, os, time
from flask_cors import CORS
import threading
import requests  # Moved up with other imports

app = Flask(__name__)
CORS(app)

DB_FILE = 'leaderboard.json'
MAX_ENTRIES = 1000
PUBLIC_TOP = 50

def load_db():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except:
        pass
    return []

def save_db(rows):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
    except:
        pass

@app.post("/submit")
def submit():
    body = request.get_json(silent=True) or {}

    player_id = (str(body.get("player_id") or "")).strip()[:64]
    name = (str(body.get("name") or "")).strip()[:24]
    score = body.get("score")
    duration = body.get("duration")

    try:
        score = int(score)
    except:
        score = 0
    try:
        duration = int(duration) if duration is not None else None
    except:
        duration = None

    if not player_id or not name or score <= 0:
        return jsonify({"ok": False, "error": "invalid_input"}), 400

    rows = load_db()

    idx = next((i for i, r in enumerate(rows) if r.get("player_id") == player_id), None)

    now_ms = int(time.time() * 1000)
    new_row = {
        "player_id": player_id,
        "name": name,
        "score": max(0, score),
        "duration": max(0, duration) if duration is not None else None,
        "ts": now_ms
    }

    if idx is None:
        rows.append(new_row)
        outcome = "inserted"
    else:
        old = rows[idx]
        old_score = int(old.get("score") or 0)
        old_dur = old.get("duration")
        better = (new_row["score"] > old_score) or (
            new_row["score"] == old_score and
            new_row["duration"] is not None and old_dur is not None and
            new_row["duration"] < old_dur
        )
        if better:
            rows[idx] = new_row
            outcome = "updated"
        else:
            old["name"] = name
            rows[idx] = old
            outcome = "kept"

    rows = rows[-MAX_ENTRIES:]
    save_db(rows)

    return jsonify({"ok": True, "result": outcome})

@app.get("/top")
def top():
    try:
        n = int(request.args.get("n", PUBLIC_TOP))
    except:
        n = PUBLIC_TOP
    n = max(1, min(n, PUBLIC_TOP))

    rows = load_db()
    rows.sort(key=lambda r: (
        -(r.get("score") or 0),
        (r.get("duration") if r.get("duration") is not None else 10**12),
        -(r.get("ts") or 0)
    ))
    public = [{"name": r.get("name",""), "score": r.get("score",0), "player_id": r.get("player_id", "")} for r in rows[:n]]
    return jsonify(public)

@app.delete("/score/<player_id>")
def delete_score(player_id):
    admin_token = request.headers.get("X-Admin-Token", "")
    if admin_token != os.environ.get("ADMIN_TOKEN", ""):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    pid = (player_id or "").strip()
    if not pid:
        return jsonify({"ok": False, "error": "invalid_player_id"}), 400

    rows = load_db()
    before = len(rows)
    rows = [r for r in rows if r.get("player_id") != pid]
    deleted = before - len(rows)

    if deleted > 0:
        save_db(rows)

    return jsonify({"ok": True, "deleted": deleted})

def keep_awake():
    """Ping self every 13 minutes to prevent sleeping (for testing)"""
    while True:
        try:
            time.sleep(13 * 60)  # Sleep for 13 minutes (testing)
            requests.get('https://leaderboard-api-2.onrender.com/top?n=50', timeout=10)
            print('Self-ping successful')
        except Exception as e:
            print(f'Self-ping failed: {e}')

# Start the keep-awake thread only in production
if os.environ.get("RENDER"):
    print("Starting keep-awake thread...")
    threading.Thread(target=keep_awake, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
