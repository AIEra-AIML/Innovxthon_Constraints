from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
import sqlite3
import csv
import io
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "innovxthon.db"
ADMIN_PASSWORD = "innovxadmin"
TOTAL_TEAMS = 40
TOTAL_ROUNDS = 4

CHALLENGES = {
    1: ("SPEAK IT", "VOICE INTERACTION"),
    2: ("LIVE WIRE", "REAL-TIME RESPONSE"),
    3: ("SHOW YOUR WHY", "EXPLAINABLE OUTPUT"),
    4: ("MAKE IT YOURS", "PERSONALIZATION"),
    5: ("BREAK THE INPUT", "ALTERNATIVE INTERACTION"),
}

app = Flask(__name__)
app.secret_key = "innovxthon-26-admin-session-key"


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_no INTEGER PRIMARY KEY,
            current_round INTEGER NOT NULL DEFAULT 1,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_no INTEGER NOT NULL,
            round_no INTEGER NOT NULL,
            challenge_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(team_no, round_no),
            UNIQUE(team_no, challenge_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('active_team','')")
    for n in range(1, TOTAL_TEAMS + 1):
        cur.execute("INSERT OR IGNORE INTO teams(team_no) VALUES(?)", (n,))
    conn.commit()
    conn.close()


def team_state(team_no):
    conn = db()
    team = conn.execute("SELECT * FROM teams WHERE team_no=?", (team_no,)).fetchone()
    if not team:
        conn.close()
        return None
    rows = conn.execute(
        "SELECT round_no, challenge_id FROM selections WHERE team_no=? ORDER BY round_no",
        (team_no,)
    ).fetchall()
    selected = [r["challenge_id"] for r in rows]
    current = conn.execute(
        "SELECT round_no, challenge_id FROM selections WHERE team_no=? AND round_no=?",
        (team_no, team["current_round"])
    ).fetchone()
    conn.close()
    done = bool(team["done"])
    return {
        "team_no": team_no,
        "round": team["current_round"],
        "done": done,
        "selected": selected,
        "current_selection": dict(current) if current else None,
        "can_select": (not done and current is None and len(selected) < TOTAL_ROUNDS),
        "total_selected": len(selected),
    }


def require_admin():
    return bool(session.get("admin"))


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/enter-team")
def enter_team():
    data = request.get_json(silent=True) or {}
    try:
        team_no = int(data.get("team_no"))
    except (TypeError, ValueError):
        return jsonify(message="Invalid team number."), 400
    if not 1 <= team_no <= TOTAL_TEAMS:
        return jsonify(message="Team number must be between 01 and 40."), 400
    conn = db()
    conn.execute("UPDATE settings SET value=? WHERE key='active_team'", (str(team_no),))
    conn.commit()
    conn.close()
    return jsonify(state=team_state(team_no))


@app.get("/api/team/<int:team_no>")
def get_team(team_no):
    if not 1 <= team_no <= TOTAL_TEAMS:
        return jsonify(message="Invalid team."), 404
    state = team_state(team_no)
    if not state:
        return jsonify(message="Team not found."), 404
    return jsonify(state)


@app.post("/api/select")
def select_challenge():
    data = request.get_json(silent=True) or {}
    try:
        team_no = int(data.get("team_no"))
        challenge_id = int(data.get("challenge_id"))
    except (TypeError, ValueError):
        return jsonify(message="Invalid selection."), 400
    if team_no < 1 or team_no > TOTAL_TEAMS or challenge_id not in CHALLENGES:
        return jsonify(message="Invalid team or challenge."), 400

    conn = db()
    conn.execute("BEGIN IMMEDIATE")
    team = conn.execute("SELECT * FROM teams WHERE team_no=?", (team_no,)).fetchone()
    if not team:
        conn.rollback(); conn.close()
        return jsonify(message="Team not found."), 404
    if team["done"]:
        conn.rollback(); conn.close()
        return jsonify(message="This team has already completed all 4 rounds."), 409

    round_no = team["current_round"]
    existing_round = conn.execute(
        "SELECT id FROM selections WHERE team_no=? AND round_no=?", (team_no, round_no)
    ).fetchone()
    if existing_round:
        conn.rollback(); conn.close()
        return jsonify(message="This round already has a challenge. Ask the admin to reset the participant screen."), 409

    used = conn.execute(
        "SELECT id FROM selections WHERE team_no=? AND challenge_id=?", (team_no, challenge_id)
    ).fetchone()
    if used:
        conn.rollback(); conn.close()
        return jsonify(message="Your team already selected this challenge in an earlier round."), 409

    conn.execute(
        "INSERT INTO selections(team_no,round_no,challenge_id) VALUES(?,?,?)",
        (team_no, round_no, challenge_id)
    )
    conn.commit(); conn.close()
    return jsonify(state=team_state(team_no))


@app.post("/api/admin/reset-participant")
def reset_participant():
    if not require_admin():
        return jsonify(message="Admin login required."), 401
    data = request.get_json(silent=True) or {}
    team_no = data.get("team_no")
    if team_no in (None, ""):
        conn = db()
        row = conn.execute("SELECT value FROM settings WHERE key='active_team'").fetchone()
        conn.close()
        team_no = row["value"] if row else ""
    try:
        team_no = int(team_no)
    except (TypeError, ValueError):
        return jsonify(message="No active team. Ask the participant to enter their team number first."), 400
    if not 1 <= team_no <= TOTAL_TEAMS:
        return jsonify(message="Invalid team."), 400

    conn = db()
    conn.execute("BEGIN IMMEDIATE")
    team = conn.execute("SELECT * FROM teams WHERE team_no=?", (team_no,)).fetchone()
    count = conn.execute("SELECT COUNT(*) AS c FROM selections WHERE team_no=?", (team_no,)).fetchone()["c"]
    if team["done"] or count >= TOTAL_ROUNDS:
        conn.rollback(); conn.close()
        return jsonify(message="This team has already completed all 4 challenges.", state=team_state(team_no)), 409
    current_round = team["current_round"]
    current_selection = conn.execute(
        "SELECT id FROM selections WHERE team_no=? AND round_no=?", (team_no, current_round)
    ).fetchone()
    if not current_selection:
        conn.rollback(); conn.close()
        return jsonify(message="The current round has not been selected yet."), 409
    next_round = current_round + 1
    if next_round > TOTAL_ROUNDS:
        conn.execute("UPDATE teams SET done=1 WHERE team_no=?", (team_no,))
    else:
        conn.execute("UPDATE teams SET current_round=? WHERE team_no=?", (next_round, team_no))
    conn.commit(); conn.close()
    return jsonify(success=True, state=team_state(team_no))


@app.post("/api/admin/reset-all")
def reset_all():
    if not require_admin():
        return jsonify(message="Admin login required."), 401
    conn = db()
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("DELETE FROM selections")
    conn.execute("UPDATE teams SET current_round=1, done=0")
    conn.execute("UPDATE settings SET value='' WHERE key='active_team'")
    conn.commit(); conn.close()
    return jsonify(success=True)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("admin_login.html", error="Incorrect admin password.")
    if not require_admin():
        return render_template("admin_login.html", error=None)
    conn = db()
    active = conn.execute("SELECT value FROM settings WHERE key='active_team'").fetchone()["value"]
    teams = []
    for n in range(1, TOTAL_TEAMS + 1):
        team = conn.execute("SELECT * FROM teams WHERE team_no=?", (n,)).fetchone()
        selections = conn.execute("""
            SELECT s.round_no, s.challenge_id FROM selections s
            WHERE s.team_no=? ORDER BY s.round_no
        """, (n,)).fetchall()
        mapping = {r["round_no"]: r["challenge_id"] for r in selections}
        teams.append({"team_no":n,"round":team["current_round"],"done":bool(team["done"]),"mapping":mapping})
    conn.close()
    active_no = int(active) if str(active).isdigit() else None
    active_state = team_state(active_no) if active_no else None
    return render_template("admin.html", teams=teams, active_team=active_no, active_state=active_state)


@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin"))


@app.get("/admin/export.csv")
def export_csv():
    if not require_admin():
        return redirect(url_for("admin"))
    conn = db()
    rows = conn.execute("""
        SELECT team_no, round_no, challenge_id, created_at
        FROM selections ORDER BY team_no, round_no
    """).fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Team", "Round", "Challenge", "Title", "Subtitle", "Selected At"])
    for r in rows:
        title, subtitle = CHALLENGES[r["challenge_id"]]
        writer.writerow([f"INX {r['team_no']:02d}", r["round_no"], f"{r['challenge_id']:02d}", title, subtitle, r["created_at"]])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment; filename=innovxthon_selections.csv"})


@app.get("/api/admin/active")
def admin_active():
    if not require_admin(): return jsonify(message="Admin login required."), 401
    conn=db(); row=conn.execute("SELECT value FROM settings WHERE key='active_team'").fetchone(); conn.close()
    active=int(row["value"]) if row and str(row["value"]).isdigit() else None
    return jsonify(active_team=active, state=team_state(active) if active else None)


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
