"""Main Flask application for the web app."""

import datetime  # pylint: disable=import-error
import os  # pylint: disable=import-error
import pymongo  # pylint: disable=import-error
from db import get_collection, USERS_COLLECTION, SESSIONS_COLLECTION, SNAPSHOTS_COLLECTION

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
users_col = get_collection(USERS_COLLECTION)
sessions_col = get_collection(SESSIONS_COLLECTION)
snapshots_col = get_collection(SNAPSHOTS_COLLECTION)

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
        return redirect(url_for("home"))
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """
    Route for the signup page
    Returns:
        rendered template (str): The rendered HTML template.
    """
    if current_user.is_authenticated:
        return redirect(url_for("home"))

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
        return redirect(url_for("home"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Route for the login page
    Returns:
        rendered template (str): The rendered HTML template.
    """
    if current_user.is_authenticated:
        return redirect(url_for("home"))

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
        return redirect(url_for("home"))

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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
