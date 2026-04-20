"""Pytest configuration for Web App tests."""

# pylint: disable=redefined-outer-name,unused-argument,import-error,import-outside-toplevel
import os
import sys
from unittest.mock import patch

import mongomock
import pytest

# Add the web-app directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# A single mock Mongo shared across the test session so imports see consistent state.
shared_mock_client = mongomock.MongoClient()
shared_mock_db = shared_mock_client["focusframe"]


@pytest.fixture(scope="session", autouse=True)
def mock_mongo():
    """Globally mock the MongoDB connection for all tests."""
    with patch("pymongo.MongoClient", return_value=shared_mock_client):
        with patch("db.get_database", return_value=shared_mock_db):
            yield shared_mock_db


@pytest.fixture
def app(mock_mongo):
    """Create and configure a Flask app instance for each test."""
    from app import app as flask_app

    flask_app.config.update(
        {"TESTING": True, "WTF_CSRF_ENABLED": False, "SECRET_KEY": "test-secret-key"}
    )
    return flask_app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's CLI commands."""
    return app.test_cli_runner()


@pytest.fixture
def authenticated_client(client, app):
    """A test client with a logged-in user."""
    from app import users_col

    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "pbkdf2:sha256:260000$dummy_hash",
    }
    users_col.delete_many({"username": "testuser"})
    result = users_col.insert_one(user_data)
    user_data["_id"] = result.inserted_id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_data["_id"])
        sess["_fresh"] = True

    return client
