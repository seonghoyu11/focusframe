"""Unit tests for the Flask web application."""

# pylint: disable=redefined-outer-name,import-error,import-outside-toplevel
import datetime
import io

from werkzeug.security import generate_password_hash


def test_index_unauthenticated(client):
    """The index page renders the login view for anonymous users."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Sign In" in response.data or b"Welcome Back" in response.data


def test_signup_get(client):
    """The signup page is reachable and shows the form."""
    response = client.get("/signup")
    assert response.status_code == 200
    assert b"Create Account" in response.data


def test_signup_post_valid(client):
    """Signing up with valid data creates a user and logs them in."""
    from app import users_col

    users_col.delete_many({"username": "newuser"})

    data = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "password123",
        "confirm_password": "password123",
    }
    response = client.post("/signup", data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome to Terminal Titans" in response.data
    assert users_col.find_one({"username": "newuser"}) is not None


def test_signup_post_mismatch_password(client):
    """Mismatched passwords surface an error and no user is created."""
    from app import users_col

    users_col.delete_many({"username": "baduser"})

    data = {
        "username": "baduser",
        "email": "bad@example.com",
        "password": "password123",
        "confirm_password": "wrongpassword",
    }
    response = client.post("/signup", data=data, follow_redirects=True)
    assert b"Passwords do not match" in response.data
    assert users_col.find_one({"username": "baduser"}) is None


def test_login_post_invalid(client):
    """Login rejects wrong passwords."""
    from app import users_col

    users_col.delete_many({"username": "loginuser"})
    users_col.insert_one(
        {"username": "loginuser", "password_hash": generate_password_hash("realpass")}
    )

    response = client.post(
        "/login",
        data={"username": "loginuser", "password": "wrongpassword"},
        follow_redirects=True,
    )
    assert b"Invalid username or password" in response.data


def test_login_post_valid(client):
    """Login accepts the correct password and greets the user."""
    from app import users_col

    users_col.delete_many({"username": "valuser"})
    users_col.insert_one(
        {"username": "valuser", "password_hash": generate_password_hash("valpass")}
    )

    response = client.post(
        "/login",
        data={"username": "valuser", "password": "valpass"},
        follow_redirects=True,
    )
    assert b"Welcome back, valuser!" in response.data
    assert response.status_code == 200


def test_dashboard_authenticated(authenticated_client):
    """The dashboard renders for a logged-in user."""
    response = authenticated_client.get("/dashboard")
    assert response.status_code == 200
    assert b"testuser" in response.data


def test_dashboard_with_active_session(authenticated_client):
    """Dashboard shows Stop Session button when a session is active."""
    from app import sessions_col, users_col

    sessions_col.delete_many({})
    user = users_col.find_one({"username": "testuser"})
    sessions_col.insert_one(
        {
            "user_id": str(user["_id"]),
            "status": "active",
            "start_time": datetime.datetime.utcnow(),
            "pomodoro_phase": "work",
            "pomodoro_phase_start": datetime.datetime.utcnow(),
            "pomodoro_cycle": 1,
        }
    )

    response = authenticated_client.get("/dashboard")
    assert response.status_code == 200
    assert b"Stop Session" in response.data


def test_start_session(authenticated_client):
    """Posting to /session/start creates a fresh active session."""
    from app import sessions_col

    sessions_col.delete_many({})
    response = authenticated_client.post("/session/start", follow_redirects=True)
    assert b"Study session started!" in response.data
    assert sessions_col.find_one({"status": "active"}) is not None


def test_stop_session(authenticated_client):
    """Posting to /session/stop marks the active session completed."""
    from app import sessions_col, users_col

    sessions_col.delete_many({})
    user = users_col.find_one({"username": "testuser"})
    sessions_col.insert_one(
        {
            "user_id": str(user["_id"]),
            "status": "active",
            "start_time": datetime.datetime.utcnow(),
        }
    )

    response = authenticated_client.post("/session/stop", follow_redirects=True)
    assert b"Study session stopped." in response.data
    assert (
        sessions_col.find_one({"user_id": str(user["_id"]), "status": "completed"})
        is not None
    )


def test_history_page(authenticated_client):
    """History page shows past completed sessions."""
    from app import sessions_col, users_col

    sessions_col.delete_many({})
    user = users_col.find_one({"username": "testuser"})
    sessions_col.insert_one(
        {
            "user_id": str(user["_id"]),
            "status": "completed",
            "start_time": datetime.datetime.utcnow() - datetime.timedelta(hours=1),
            "end_time": datetime.datetime.utcnow(),
        }
    )

    response = authenticated_client.get("/history")
    assert response.status_code == 200
    assert b"Session History" in response.data


def test_session_detail_page(authenticated_client):
    """Session detail page renders for a valid session id."""
    from app import sessions_col, snapshots_col, users_col

    sessions_col.delete_many({})
    snapshots_col.delete_many({})
    user = users_col.find_one({"username": "testuser"})
    sess_id = sessions_col.insert_one(
        {
            "user_id": str(user["_id"]),
            "status": "completed",
            "start_time": datetime.datetime.utcnow(),
        }
    ).inserted_id

    snapshots_col.insert_one(
        {
            "session_id": sess_id,
            "classification": "focused",
            "timestamp": datetime.datetime.utcnow(),
            "emotion": "neutral",
            "image": b"fake_image_data",
        }
    )

    response = authenticated_client.get(f"/session/{str(sess_id)}")
    assert response.status_code == 200
    assert b"Session Detail" in response.data
    assert b"focused" in response.data.lower()


def test_dashboard_stats_two_class(authenticated_client):
    """Dashboard stats compute correctly"""
    from app import sessions_col, snapshots_col, users_col

    sessions_col.delete_many({})
    snapshots_col.delete_many({})
    user = users_col.find_one({"username": "testuser"})
    sess_id = sessions_col.insert_one(
        {
            "user_id": str(user["_id"]),
            "status": "completed",
            "start_time": datetime.datetime.utcnow(),
        }
    ).inserted_id

    for classification in ("focused", "focused", "distracted", "distracted"):
        snapshots_col.insert_one(
            {
                "session_id": sess_id,
                "classification": classification,
                "timestamp": datetime.datetime.utcnow(),
            }
        )

    response = authenticated_client.get("/dashboard")
    assert response.status_code == 200
    # 50% focus rate should appear in the summary totals
    assert b"50" in response.data


def test_session_state_no_active(authenticated_client):
    """/session/state returns active=false when no session is running."""
    from app import sessions_col

    sessions_col.delete_many({})
    response = authenticated_client.get("/session/state")
    assert response.status_code == 200
    data = response.get_json()
    assert data["active"] is False


def test_session_state_active(authenticated_client):
    """/session/state returns live Pomodoro + stats fields for an active session."""
    from app import sessions_col, snapshots_col, users_col

    sessions_col.delete_many({})
    snapshots_col.delete_many({})
    user = users_col.find_one({"username": "testuser"})
    sess_id = sessions_col.insert_one(
        {
            "user_id": str(user["_id"]),
            "status": "active",
            "start_time": datetime.datetime.utcnow(),
            "pomodoro_phase": "work",
            "pomodoro_phase_start": datetime.datetime.utcnow(),
            "pomodoro_cycle": 1,
        }
    ).inserted_id
    snapshots_col.insert_one(
        {
            "session_id": sess_id,
            "classification": "focused",
            "timestamp": datetime.datetime.utcnow(),
        }
    )

    response = authenticated_client.get("/session/state")
    assert response.status_code == 200
    data = response.get_json()
    assert data["active"] is True
    assert data["phase"] == "WORK"
    assert "timer" in data
    assert "progress" in data
    assert data["focused_time"] == 10
    assert data["distracted_time"] == 0


def test_snapshot_upload_no_session(authenticated_client):
    """/session/snapshot returns 400 when no active session exists."""
    from app import sessions_col

    sessions_col.delete_many({})
    response = authenticated_client.post(
        "/session/snapshot",
        data={"image": (io.BytesIO(b"fake_jpeg_bytes"), "snap.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_snapshot_upload_success(authenticated_client):
    """/session/snapshot accepts an upload and writes an unanalyzed snapshot."""
    from app import sessions_col, snapshots_col, users_col

    sessions_col.delete_many({})
    snapshots_col.delete_many({})
    user = users_col.find_one({"username": "testuser"})
    sess_id = sessions_col.insert_one(
        {
            "user_id": str(user["_id"]),
            "status": "active",
            "start_time": datetime.datetime.utcnow(),
            "snapshot_count": 0,
        }
    ).inserted_id

    response = authenticated_client.post(
        "/session/snapshot",
        data={"image": (io.BytesIO(b"fake_jpeg_bytes"), "snap.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 204

    stored = snapshots_col.find_one({"session_id": sess_id})
    assert stored is not None
    assert stored["analyzed"] is False
    assert stored["classification"] is None
    assert stored["image"] == b"fake_jpeg_bytes"


def test_snapshot_upload_missing_image(authenticated_client):
    """/session/snapshot returns 400 when no image file is provided."""
    from app import sessions_col, users_col

    sessions_col.delete_many({})
    user = users_col.find_one({"username": "testuser"})
    sessions_col.insert_one(
        {
            "user_id": str(user["_id"]),
            "status": "active",
            "start_time": datetime.datetime.utcnow(),
        }
    )

    response = authenticated_client.post("/session/snapshot", data={})
    assert response.status_code == 400


def test_logout(authenticated_client):
    """Logout clears the session and redirects to the login landing."""
    response = authenticated_client.get("/logout", follow_redirects=True)
    assert b"Welcome Back" in response.data or b"Sign In" in response.data
