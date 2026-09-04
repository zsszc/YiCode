"""
Phase 3 测试 — Auth + LLM Provider
"""

import pytest
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.models.user import User


class TestSecurity:
    def test_password_hash(self):
        hashed = get_password_hash("test123")
        assert verify_password("test123", hashed)
        assert not verify_password("wrong", hashed)

    def test_jwt_token(self):
        token = create_access_token({"sub": "1", "username": "test"})
        payload = decode_access_token(token)
        assert payload["sub"] == "1"
        assert payload["username"] == "test"

    def test_jwt_invalid(self):
        payload = decode_access_token("invalid.token.here")
        assert payload is None


class TestAuthAPI:
    def test_register(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "testpass123",
            "email": "test@example.com",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_register_duplicate_username(self, client, db_session):
        db_session.add(User(username="dupuser", hashed_password=get_password_hash("pass")))
        db_session.commit()

        resp = client.post("/api/v1/auth/register", json={
            "username": "dupuser",
            "password": "testpass123",
        })
        assert resp.status_code == 400

    def test_login_success(self, client, db_session):
        db_session.add(User(username="loginuser", hashed_password=get_password_hash("mypassword")))
        db_session.commit()

        resp = client.post("/api/v1/auth/login", json={
            "username": "loginuser",
            "password": "mypassword",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, db_session):
        db_session.add(User(username="wrongpass", hashed_password=get_password_hash("rightpass")))
        db_session.commit()

        resp = client.post("/api/v1/auth/login", json={
            "username": "wrongpass",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_me_without_token(self, client):
        """无 token 时返回默认用户（向后兼容）。"""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1

    def test_me_with_token(self, client, db_session):
        db_session.add(User(id=2, username="tokenuser", hashed_password=get_password_hash("pass")))
        db_session.commit()
        token = create_access_token({"sub": "2", "username": "tokenuser"})

        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "tokenuser"
