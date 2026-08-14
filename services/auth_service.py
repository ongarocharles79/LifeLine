"""
Phase 1 demo authentication.

NOT PRODUCTION-GRADE. This uses a simple salted+peppered SHA-256 hash shaped
as `scheme$salt$digest` specifically so it can be swapped for a real
Argon2id-based scheme later without changing any call site (hash_password /
verify_password / authenticate / login / logout keep the same signatures).

Do not reuse this scheme outside of the Phase 1 demo environment.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

import streamlit as st
from sqlalchemy.orm import Session

from config.settings import AUTH_PEPPER
from database.models import User

_SCHEME = "sha256demo"


def hash_password(plain: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}{AUTH_PEPPER}{plain}".encode()).hexdigest()
    return f"{_SCHEME}${salt}${digest}"


def verify_password(plain: str, encoded_hash: str) -> bool:
    try:
        scheme, salt, digest = encoded_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != _SCHEME:
        return False
    expected = hashlib.sha256(f"{salt}{AUTH_PEPPER}{plain}".encode()).hexdigest()
    return secrets.compare_digest(expected, digest)


def authenticate(session: Session, email: str, password: str) -> User | None:
    user = session.query(User).filter(User.email == email.strip().lower(), User.is_active.is_(True)).first()
    if user is None or not verify_password(password, user.password_hash):
        return None
    user.last_login_at = datetime.utcnow()
    session.add(user)
    session.commit()
    return user


def login(session: Session, email: str, password: str) -> bool:
    user = authenticate(session, email, password)
    if user is None:
        return False
    st.session_state["auth_user"] = {
        "id": user.id,
        "email": user.email,
        "role": user.role.value,
        "full_name": user.full_name,
    }
    return True


def logout() -> None:
    st.session_state.pop("auth_user", None)
    st.rerun()


def current_user() -> dict | None:
    return st.session_state.get("auth_user")


def is_authenticated() -> bool:
    return "auth_user" in st.session_state
