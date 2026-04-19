"""Main Flask application for the web app."""

import datetime  # pylint: disable=import-error
import os  # pylint: disable=import-error
from collections import Counter

from dotenv import load_dotenv
from bson.objectid import ObjectId  # pylint: disable=import-error
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

from db import (
    get_database,
    USERS_COLLECTION,
    SESSIONS_COLLECTION,
    SNAPSHOTS_COLLECTION,
)

try:
    from zoneinfo import ZoneInfo

    ZoneInfo("America/New_York")
except (ImportError, AttributeError):
    try:
        import importlib

        importlib.import_module("tzdata")
    except (ImportError, AttributeError):
        from datetime import timezone as _tz

        class ZoneInfo:  # pylint: disable=too-few-public-methods
            """Fallback ZoneInfo class for environments without zoneinfo/tzdata."""

            _map = {
                "America/New_York": _tz(datetime.timedelta(hours=-5)),
                "UTC": _tz.utc,
            }

            def __init__(self, key):
                self._offset = self._map.get(key, _tz.utc)


# load .env
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

# connect to MongoDB using db helper
db = get_database()

users_col = db[USERS_COLLECTION]
sessions_col = db[SESSIONS_COLLECTION]
snapshots_col = db[SNAPSHOTS_COLLECTION]

# flask-login set up
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access that page."
login_manager.login_message_category = "info"


# user information
class User(UserMixin):
    """User class for Flask-Login integration."""

    def __init__(self, user_doc):
        """Initializes the User class."""
        self.user_doc = user_doc

    def get_id(self):
        """Returns the user's ID."""
        return str(self.user_doc["_id"])

    @property
    def username(self):
        """Returns the username of the user."""
        return self.user_doc.get("username", "")

    @property
    def email(self):
        """Returns the email of the user."""
        return self.user_doc.get("email", "")


@login_manager.user_loader
def load_user(user_id):
    """Loads a user from the database given their ID."""
    try:
        doc = users_col.find_one({"_id": ObjectId(user_id)})
    except Exception:  # pylint: disable=broad-exception-caught
        return None
    return User(doc) if doc else None


@app.before_request
def check_auth():
    """
    Global authentication check. Redirects unauthenticated users to the
    login page for all routes except those in the public_endpoints list.
    """
    public_endpoints = ["index", "login", "signup", "static"]
    if not current_user.is_authenticated and request.endpoint not in public_endpoints:
        return redirect(url_for("login"))
    return None


@app.route("/")
def index():
    """
    Route for the index page
    Returns:
        rendered template (str): The rendered HTML template.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/dashboard")
@login_required
def dashboard():
    """
    Dashboard for displaying session stats and controls.
    """
    user_id = current_user.get_id()
    active_session = sessions_col.find_one({"user_id": user_id, "status": "active"})
    # Fetch up to 2 past sessions
    past_sessions_cursor = (
        sessions_col.find({"user_id": user_id, "status": "completed"})
        .sort("start_time", -1)
        .limit(2)
    )
    past_sessions = list(past_sessions_cursor)

    # Calculate stats for all fetched sessions
    def calculate_stats(session_id):
        fc = snapshots_col.count_documents(
            {"session_id": session_id, "classification": "focused"}
        )
        dc = snapshots_col.count_documents(
            {"session_id": session_id, "classification": "distracted"}
        )
        ac = snapshots_col.count_documents(
            {"session_id": session_id, "classification": "absent"}
        )
        tt = (fc + dc + ac) * 10
        ft = fc * 10
        dt = dc * 10
        at = ac * 10
        rate = (ft / tt * 100) if tt > 0 else 0
        return {
            "focused_time": ft,
            "distracted_time": dt,
            "absent_time": at,
            "total_time": tt,
            "focus_rate": rate,
        }

    pomodoro = None
    stats = None
    if active_session:
        stats = calculate_stats(active_session["_id"])
        pom_start = active_session.get(
            "pomodoro_phase_start", active_session["start_time"]
        )
        cycle = active_session.get("pomodoro_cycle", 1)
        delta = datetime.datetime.utcnow() - pom_start
        elapsed = delta.total_seconds()
        current_phase = active_session.get("pomodoro_phase", "work")
        if current_phase == "work":
            rem = max(0, (25 * 60) - elapsed)
            if rem == 0:
                current_phase = "break"
                rem = 25 * 60
        else:
            rem = max(0, (5 * 60) - elapsed)
            if rem == 0:
                current_phase = "work"
                cycle += 1
                rem = 25 * 60
        pomodoro = {
            "phase": current_phase.upper(),
            "timer": f"{int(rem // 60):02d}:{int(rem % 60):02d}",
            "cycle": cycle,
        }
    elif past_sessions:
        stats = calculate_stats(past_sessions[0]["_id"])
    for ps in past_sessions:
        ps["stats"] = calculate_stats(ps["_id"])
    return redirect(url_for("index"))


@app.route("/session/start", methods=["POST"])
@login_required
def start_session():
    """Starts a new focus session."""
    existing = sessions_col.find_one(
        {"user_id": current_user.get_id(), "status": "active"}
    )
    if existing:
        flash("A session is already active.", "error")
        return redirect(url_for("dashboard"))

    now = datetime.datetime.utcnow()
    new_session = {
        "user_id": current_user.get_id(),
        "status": "active",
        "start_time": now,
        "end_time": None,
        "pomodoro_phase": "work",
        "pomodoro_phase_start": now,
        "pomodoro_cycle": 1,
        "total_focused_seconds": 0,
        "total_distracted_seconds": 0,
        "total_absent_seconds": 0,
        "snapshot_count": 0,
        "notification": None,
    }
    sessions_col.insert_one(new_session)
    flash("Study session started!", "success")
    return redirect(url_for("dashboard"))


@app.route("/session/stop", methods=["POST"])
@login_required
def stop_session():
    """Stops the current focus session."""
    sessions_col.update_one(
        {"user_id": current_user.get_id(), "status": "active"},
        {"$set": {"status": "completed", "end_time": datetime.datetime.utcnow()}},
    )
    flash("Study session stopped.", "info")
    return redirect(url_for("dashboard"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """
    Route for the signup page
    Returns:
        rendered template (str): The rendered HTML template.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        error = None
        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif users_col.find_one({"email": email}):
            error = "An account with that email already exists."
        elif users_col.find_one({"username": username}):
            error = "That username is already taken."

        if error:
            flash(error, "error")
            return render_template("signup.html", username=username, email=email)

        # hash password
        new_user = {
            "username": username,
            "password_hash": generate_password_hash(password),
            "created_at": datetime.datetime.utcnow(),
            "role": None,
        }
        result = users_col.insert_one(new_user)
        new_user["_id"] = result.inserted_id

        # log in after signing up
        login_user(User(new_user))
        flash(f"Welcome to Terminal Titans, {username}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Route for the login page
    Returns:
        rendered template (str): The rendered HTML template.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        error = None
        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."

        if error:
            flash(error, "error")
            return render_template("login.html", username=username)

        user_doc = users_col.find_one({"username": username})
        if not user_doc or not check_password_hash(user_doc["password_hash"], password):
            flash("Invalid username or password.", "error")
            return render_template("login.html", username=username)

        login_user(User(user_doc))
        flash(f"Welcome back, {username}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """
    Route for the logout page
    Returns:
        rendered template (str): The rendered HTML template.
    """
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/history")
@login_required
def history():  # pylint: disable=too-many-locals
    """
    Shows a table of all past sessions.
    """
    user_id = current_user.get_id()
    past_sessions_cursor = sessions_col.find(
        {"user_id": user_id, "status": "completed"}
    ).sort("start_time", -1)

    sessions_list = []
    for sess in past_sessions_cursor:
        sess_id = sess["_id"]
        fc = snapshots_col.count_documents(
            {"session_id": sess_id, "classification": "focused"}
        )
        dc = snapshots_col.count_documents(
            {"session_id": sess_id, "classification": "distracted"}
        )
        ac = snapshots_col.count_documents(
            {"session_id": sess_id, "classification": "absent"}
        )
        tt = (fc + dc + ac) * 10
        ft = fc * 10
        dt = dc * 10
        rate = (ft / tt * 100) if tt > 0 else 0
        distract_rate = (dt / tt * 100) if tt > 0 else 0

        duration = 0
        if sess.get("end_time"):
            duration = int((sess["end_time"] - sess["start_time"]).total_seconds() / 60)

        emotions = [
            str(x.get("emotion", "None"))
            for x in snapshots_col.find({"session_id": sess_id}, {"emotion": 1})
        ]
        dom_emotion = "None"
        if emotions:
            try:
                dom_emotion = Counter(emotions).most_common(1)[0][0]
            except (IndexError, KeyError):
                dom_emotion = "None"

        sess_data = {
            "id": str(sess_id),
            "date": sess["start_time"].strftime("%Y-%m-%d"),
            "start_time": sess["start_time"].strftime("%H:%M"),
            "end_time": sess["end_time"].strftime("%H:%M") if sess.get("end_time") else "—",
            "duration": duration,
            "focused_percent": rate,
            "distracted_percent": distract_rate,
            "dominant_emotion": dom_emotion,
        }
        sessions_list.append(sess_data)
    return render_template("history.html", sessions=sessions_list)


@app.route("/session/<session_id>")
@login_required
def session_detail(session_id):
    """
    Shows detailed stats of a specific past session (Page 5).
    """
    try:
        sess = sessions_col.find_one(
            {"_id": ObjectId(session_id), "user_id": current_user.get_id()}
        )
    except Exception:  # pylint: disable=broad-exception-caught
        sess = None

    if not sess:
        flash("Session not found.", "error")
        return redirect(url_for("history"))

    # stats calculation
    fc = snapshots_col.count_documents({"session_id": sess["_id"], "classification": "focused"})
    dc = snapshots_col.count_documents({"session_id": sess["_id"], "classification": "distracted"})
    ac = snapshots_col.count_documents({"session_id": sess["_id"], "classification": "absent"})
    
    tt = (fc + dc + ac) * 10
    ft = fc * 10
    dt = dc * 10
    at = ac * 10
    rate = (ft / tt * 100) if tt > 0 else 0
    distract_rate = (dt / tt * 100) if tt > 0 else 0

    stats = {
        "focused_time": ft,
        "distracted_time": dt,
        "absent_time": at,
        "total_time": tt,
        "focus_rate": rate,
        "distract_rate": distract_rate,
        "dash_offset": 408.4 * (1 - rate / 100),
    }

    # Fetch snapshots with base64 images
    import base64  # pylint: disable=import-outside-toplevel
    raw_snaps = list(snapshots_col.find({"session_id": sess["_id"]}).sort("timestamp", 1))
    snapshots = []
    for snap in raw_snaps:
        img_b64 = None
        if snap.get("image"):
            img_b64 = base64.b64encode(snap["image"]).decode("utf-8")
        snapshots.append({
            "timestamp": snap["timestamp"].strftime("%H:%M:%S"),
            "emotion": snap.get("emotion", "unknown"),
            "confidence": snap.get("confidence", 0),
            "classification": snap.get("classification", "unknown"),
            "image_b64": img_b64,
        })

    return render_template("session_detail.html", session=sess, stats=stats, snapshots=snapshots)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
