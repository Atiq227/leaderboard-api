from flask import Flask, request, jsonify
import json, os, time

app = Flask(__name__)

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
    name = (body.get('name') or '').strip()[:24]
    score = body.get('score')
    duration = body.get('duration')

    try:
        score = int(score)
    except:
        score = 0
    try:
        duration = int(duration) if duration is not None else None
    except:
        duration = None

    if not name or score <= 0:
        return jsonify({"ok": False, "error": "invalid_input"}), 400

    rows = load_db()
    rows.append({
        "name": name,
        "score": max(0, score),
        "duration": max(0, duration) if duration is not None else None,
        "ts": int(time.time()*1000)
    })

    rows.sort(key=lambda r: (-r["score"],
                             r["duration"] if r["duration"] is not None else 999999,
                             r["ts"]))
    rows = rows[:MAX_ENTRIES]
    save_db(rows)
    return jsonify({"ok": True})

@app.get("/top")
def top():
    try:
        n = int(request.args.get("n", 10))
    except:
        n = 10
    n = min(n, PUBLIC_TOP)
    rows = load_db()[:n]
    return jsonify([
        {"name": r["name"], "score": r["score"], "duration": r.get("duration"), "ts": r["ts"]}
        for r in rows
    ])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))