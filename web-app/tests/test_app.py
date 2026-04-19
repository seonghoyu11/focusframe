"""Unit tests for the Flask web application."""

# pylint: disable=redefined-outer-name,import-error,import-outside-toplevel
import datetime
from werkzeug.security import generate_password_hash


def test_index_unauthenticated(client):
    """Test that the index page is accessible and shows login."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Sign In" in response.data or b"Welcome Back" in response.data


def test_signup_get(client):
    """Test that the signup page is accessible."""
    response = client.get("/signup")
    assert response.status_code == 200
    assert b"Create Account" in response.data


def test_signup_post_valid(client):
    """Test signing up with valid data."""
    # pylint: disable=import-outside-toplevel,import-error
    from app import users_col

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
    """Test signing up with mismatched passwords."""
    data = {
        "username": "baduser",
        "email": "bad@example.com",
        "password": "password123",
        "confirm_password": "wrongpassword",
    }
    response = client.post("/signup", data=data, follow_redirects=True)
    assert b"Passwords do not match" in response.data


def test_login_post_invalid(client):
    """Test login with invalid credentials."""
    # pylint: disable=import-outside-toplevel,import-error
    from app import users_col

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
    """Test login with valid credentials."""
    # pylint: disable=import-outside-toplevel,import-error
    from app import users_col

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


def test_dashboard_authenticated(
    authenticated_client,
):  # pylint: disable=redefined-outer-name
    """Test that the dashboard is accessible for authenticated users."""
    response = authenticated_client.get("/dashboard")
    assert response.status_code == 200
    assert b"testuser" in response.data
    assert b"Focused" in response.data


def test_dashboard_with_active_session(
    authenticated_client,
):  # pylint: disable=redefined-outer-name
    """Test dashboard display when there is an active session."""
    # pylint: disable=import-outside-toplevel,import-error
    from app import users_col, sessions_col

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


def test_start_session(authenticated_client):  # pylint: disable=redefined-outer-name
    """Test starting a new session."""
    # pylint: disable=import-outside-toplevel,import-error
    from app import sessions_col

    sessions_col.delete_many({})
    response = authenticated_client.post("/session/start", follow_redirects=True)
    assert b"Study session started!" in response.data
    assert sessions_col.find_one({"status": "active"}) is not None


def test_stop_session(authenticated_client):  # pylint: disable=redefined-outer-name
    """Test stopping an active session."""
    # pylint: disable=import-outside-toplevel,import-error
    from app import users_col, sessions_col

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


def test_history_page(authenticated_client):  # pylint: disable=redefined-outer-name
    """Test the history page retrieval."""
    # pylint: disable=import-outside-toplevel,import-error
    from app import users_col, sessions_col

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


def test_session_detail_page(
    authenticated_client,
):  # pylint: disable=redefined-outer-name
    """Test the session detail page."""
    # pylint: disable=import-outside-toplevel,import-error
    from app import users_col, sessions_col, snapshots_col

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
            "emotion": "happy",
            "image": b"fake_image_data",
        }
    )

    response = authenticated_client.get(f"/session/{str(sess_id)}")
    assert response.status_code == 200
    assert b"Session Detail" in response.data
    assert b"focused" in response.data.lower()


def test_dashboard_stats_logic(
    authenticated_client,
):  # pylint: disable=redefined-outer-name
    """Verify that the dashboard correctly calculates study statistics (Coverage boost)."""
    # pylint: disable=import-outside-toplevel,import-error
    from app import users_col, sessions_col, snapshots_col

    user = users_col.find_one({"username": "testuser"})
    sess_id = sessions_col.insert_one(
        {
            "user_id": str(user["_id"]),
            "status": "completed",
            "start_time": datetime.datetime.utcnow(),
        }
    ).inserted_id

    # Add 2 focused snapshots, 1 distracted, 1 absent
    # Each snapshot represents 10 seconds in the current math logic
    snapshots_col.insert_one(
        {
            "session_id": sess_id,
            "classification": "focused",
            "timestamp": datetime.datetime.utcnow(),
        }
    )
    snapshots_col.insert_one(
        {
            "session_id": sess_id,
            "classification": "focused",
            "timestamp": datetime.datetime.utcnow(),
        }
    )
    snapshots_col.insert_one(
        {
            "session_id": sess_id,
            "classification": "distracted",
            "timestamp": datetime.datetime.utcnow(),
        }
    )
    snapshots_col.insert_one(
        {
            "session_id": sess_id,
            "classification": "absent",
            "timestamp": datetime.datetime.utcnow(),
        }
    )

    response = authenticated_client.get("/dashboard")
    assert response.status_code == 200
    # 2 focused out of 4 total = 50%
    assert b"50" in response.data or b"50.0" in response.data


def test_logout(authenticated_client):  # pylint: disable=redefined-outer-name
    """Test logging out."""
    response = authenticated_client.get("/logout", follow_redirects=True)
    assert b"Welcome Back" in response.data or b"Sign In" in response.data
