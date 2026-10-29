"""Tenants, users, tokens. Password hashing via stdlib PBKDF2 (no external deps)."""
from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass

from ..core.db import Database, new_id, now_iso, token_string
from ..core.errors import AuthError, NotFoundError, ValidationError

PBKDF2_ROUNDS = 120_000
TOKEN_TTL_DAYS = 90

KRA_PIN_RE = re.compile(r"^(A|P)[0-9]{9}[A-Z]$", re.I)


def validate_kra_pin(pin: str | None) -> str | None:
    """KRA PIN format: letter + 9 digits + check letter (e.g. A123456789Z)."""
    if pin is None or pin == "":
        return None
    p = pin.strip().upper()
    if not KRA_PIN_RE.match(p):
        raise ValidationError(f"invalid KRA PIN '{pin}' (expected e.g. A012345678X)")
    return p


def normalize_phone(phone: str | None) -> str | None:
    """Normalize to +254 form where possible."""
    if not phone:
        return None
    d = re.sub(r"[^0-9+]", "", phone)
    if d.startswith("07") or d.startswith("01"):
        return "+254" + d[1:]
    if d.startswith("254"):
        return "+" + d
    if d.startswith("+254"):
        return d
    return phone  # leave landlines/intl as-is


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, hexdigest = stored.split("$")
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return secrets.compare_digest(dk.hex(), hexdigest)


@dataclass
class AuthContext:
    """Everything downstream services need: who, which tenant, what surface."""
    user_id: str
    tenant_id: str
    role: str
    email: str
    surface: str  # api | cli | mcp

    @property
    def is_owner(self) -> bool:
        return self.role in ("owner", "platform_admin")


class TenantService:
    def __init__(self, db: Database):
        self.db = db

    def create_tenant(self, name: str, kra_pin: str | None = None, phone: str | None = None,
                      plan_id: str = "starter") -> dict:
        if not name or not name.strip():
            raise ValidationError("tenant name required")
        tid = new_id("tnt")
        self.db.exec(
            "INSERT INTO tenants(id,name,kra_pin,phone,plan_id,status,created_at) VALUES(?,?,?,?,?,?,?)",
            (tid, name.strip(), validate_kra_pin(kra_pin), normalize_phone(phone), plan_id, "active", now_iso()))
        return self.get_tenant(tid)

    def get_tenant(self, tenant_id: str) -> dict:
        row = self.db.one("SELECT * FROM tenants WHERE id=?", (tenant_id,))
        if not row:
            raise NotFoundError(f"tenant '{tenant_id}' not found")
        return row

    def list_tenants(self) -> list[dict]:
        return self.db.query("SELECT * FROM tenants ORDER BY created_at")

    def update_plan(self, tenant_id: str, plan_id: str) -> dict:
        self.get_tenant(tenant_id)
        self.db.exec("UPDATE tenants SET plan_id=? WHERE id=?", (plan_id, tenant_id))
        return self.get_tenant(tenant_id)


class UserService:
    def __init__(self, db: Database, tenants: TenantService):
        self.db = db
        self.tenants = tenants

    def register_user(self, email: str, password: str, tenant_name: str,
                      kra_pin: str | None = None, phone: str | None = None,
                      plan_id: str = "starter") -> tuple[dict, str]:
        """Create tenant + owner user in one shot; returns (user, api_token)."""
        if not email or "@" not in email:
            raise ValidationError("valid email required")
        if len(password or "") < 8:
            raise ValidationError("password must be at least 8 characters")
        tenant = self.tenants.create_tenant(tenant_name, kra_pin, phone, plan_id)
        user = self.add_user(email, password, tenant["id"], role="owner")
        token = self.issue_token(user["id"], kind="api")
        return user, token

    def add_user(self, email: str, password: str, tenant_id: str, role: str = "staff") -> dict:
        self.tenants.get_tenant(tenant_id)
        uid = new_id("usr")
        self.db.exec("INSERT INTO users(id,tenant_id,email,pw_hash,role,created_at) VALUES(?,?,?,?,?,?)",
                     (uid, tenant_id, email.lower().strip(), hash_password(password), role, now_iso()))
        return self.get_user(uid)

    def get_user(self, user_id: str) -> dict:
        row = self.db.one("SELECT * FROM users WHERE id=?", (user_id,))
        if not row:
            raise NotFoundError("user not found")
        return row

    def count_users(self, tenant_id: str) -> int:
        r = self.db.one("SELECT COUNT(*) c FROM users WHERE tenant_id=?", (tenant_id,))
        return r["c"] if r else 0

    def login(self, email: str, password: str, kind: str = "api") -> tuple[AuthContext, str]:
        row = self.db.one("SELECT * FROM users WHERE email=?", ((email or "").lower().strip(),))
        if not row or not verify_password(password or "", row["pw_hash"]):
            raise AuthError("invalid credentials")
        token = self.issue_token(row["id"], kind=kind)
        return self.context_from_token(token, surface=kind), token

    def issue_token(self, user_id: str, kind: str = "api") -> str:
        self.get_user(user_id)
        raw = token_string()
        h = hashlib.sha256(raw.encode()).hexdigest()
        from datetime import datetime, timedelta, timezone
        exp = (datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.db.exec("INSERT INTO tokens(token_hash,user_id,kind,expires_at,created_at) VALUES(?,?,?,?,?)",
                     (h, user_id, kind, exp, now_iso()))
        return raw

    def revoke_token(self, raw_token: str) -> None:
        h = hashlib.sha256(raw_token.encode()).hexdigest()
        self.db.exec("DELETE FROM tokens WHERE token_hash=?", (h,))

    def context_from_token(self, raw_token: str, surface: str | None = None) -> AuthContext:
        h = hashlib.sha256(raw_token.encode()).hexdigest()
        tok = self.db.one("SELECT * FROM tokens WHERE token_hash=?", (h,))
        if not tok:
            raise AuthError("invalid token")
        if tok["expires_at"] and tok["expires_at"] < now_iso():
            raise AuthError("token expired")
        user = self.get_user(tok["user_id"])
        if not user["tenant_id"]:
            raise AuthError("user has no tenant")
        tenant = self.tenants.get_tenant(user["tenant_id"])
        if tenant["status"] != "active":
            raise AuthError(f"tenant status is {tenant['status']}")
        return AuthContext(user_id=user["id"], tenant_id=user["tenant_id"], role=user["role"],
                           email=user["email"], surface=surface or tok["kind"])
