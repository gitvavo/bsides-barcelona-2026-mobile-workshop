"""Mockapp workshop API. INTENTIONALLY VULNERABLE: isolated lab use only."""
import hashlib
import hmac
import re
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

DB = Path(os.getenv("MOCKAPP_DB", "/mnt/mockapp/database/mockapp.sqlite3"))
app = FastAPI(title="Mockapp Workshop API", version="0.5.1")
PARTICIPANT_START_POINTS = 420
USERS = [
    (1042, "alice", "Alice", "coffee1042", 420, 0),
    (1043, "bob", "Bob", "coffee1043", 850, 0),
    (1044, "charlie", "Charlie", "coffee1044", 60, 0),
    (1045, "dana", "Dana", "coffee1045", 0, 0),
    (9001, "emma", "Emma", "coffee9001", 2000, 1),
]
REWARDS = [(1, "Espresso", 100), (2, "Cappuccino", 200),
           (3, "Croissant", 250), (4, "€5 voucher", 500),
           (5, "Mockapp Cupcake", 9999)]

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout = 10000")
    return db

def initialize(db):
    # Preserve the earlier stage-1 database while adding training tables.
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, points INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS rewards (id INTEGER PRIMARY KEY, name TEXT NOT NULL, cost INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS accounts (user_id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0, approved INTEGER NOT NULL DEFAULT 1, is_participant INTEGER NOT NULL DEFAULT 0)")
    # In-place migration: existing seeded/demo accounts remain active.
    columns = {r["name"] for r in db.execute("PRAGMA table_info(accounts)")}
    if "approved" not in columns:
        db.execute("ALTER TABLE accounts ADD COLUMN approved INTEGER NOT NULL DEFAULT 1")
    if "is_participant" not in columns:
        db.execute("ALTER TABLE accounts ADD COLUMN is_participant INTEGER NOT NULL DEFAULT 0")
    db.execute("CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, description TEXT NOT NULL, delta INTEGER NOT NULL, created_at INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS redemptions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, reward_id INTEGER NOT NULL, charged_points INTEGER NOT NULL, created_at INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS point_transfers (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER NOT NULL, recipient_id INTEGER NOT NULL, amount INTEGER NOT NULL, created_at INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS partner_promotions (user_id INTEGER PRIMARY KEY, created_at INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS workshop_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    db.execute("INSERT OR IGNORE INTO workshop_settings(key,value) VALUES('solutions_released','0')")
    db.executemany("INSERT OR IGNORE INTO users(id,name,points) VALUES(?,?,?)", [(u[0], u[2], u[4]) for u in USERS])
    db.executemany("INSERT OR IGNORE INTO accounts(user_id,username,password,is_admin) VALUES(?,?,?,?)", [(u[0],u[1],u[3],u[5]) for u in USERS])
    db.executemany("INSERT OR IGNORE INTO rewards VALUES (?,?,?)", REWARDS)
    if not db.execute("SELECT 1 FROM transactions LIMIT 1").fetchone():
        for uid, _, _, _, points, _ in USERS:
            db.execute("INSERT INTO transactions(user_id,description,delta,created_at) VALUES(?,?,?,?)", (uid,"Welcome bonus and coffee purchases",points,int(time.time())))

@app.on_event("startup")
def setup():
    with connect() as db:
        initialize(db)

def make_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
    return "scrypt$" + salt.hex() + "$" + digest.hex()

def password_matches(password: str, stored: str) -> bool:
    # Pre-existing seeded demo accounts use legacy plaintext passwords.
    if not stored.startswith("scrypt$"):
        return hmac.compare_digest(password.encode("utf-8"), stored.encode("utf-8"))
    try:
        _, salt_hex, digest_hex = stored.split("$", 2)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=16384, r=8, p=1)
        return hmac.compare_digest(digest, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False

def current_user(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization[7:]
    with connect() as db:
        row = db.execute("SELECT a.user_id, a.username, a.is_admin FROM sessions s JOIN accounts a ON s.user_id=a.user_id WHERE s.token=?", (token,)).fetchone()
    if not row:
        raise HTTPException(401, "Invalid bearer token")
    return dict(row)

class Login(BaseModel):
    username: str
    password: str

class Registration(BaseModel):
    username: str = Field(min_length=3, max_length=24)
    password: str = Field(min_length=8, max_length=128)

class Redemption(BaseModel):
    reward_id: int
    # INTENTIONAL VULNERABILITY: client-provided cost overrides the catalogue price.
    cost_points: Optional[int] = Field(default=None, ge=0, le=100000)

class PointsTransfer(BaseModel):
    to_user: str
    points: int

@app.get("/api/v1/health")
def health():
    with connect() as db:
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return {"status":"ok","app":"Mockapp","database":"sqlite","seeded_users":count,"version":"0.5.1"}

@app.get("/api/v1/workshop-state")
def workshop_state():
    with connect() as db:
        row = db.execute("SELECT value FROM workshop_settings WHERE key='solutions_released'").fetchone()
    return {"solutions_released": bool(row and row["value"] == "1")}

@app.post("/api/v1/register", status_code=201)
def register(body: Registration):
    username = body.username.strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,23}", username):
        raise HTTPException(400, "Username must be 3–24 characters: letters, digits or underscore; start with a letter")
    password_hash = make_password(body.password)
    now = int(time.time())
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM accounts WHERE username=?", (username,)).fetchone():
            raise HTTPException(409, "Username is already taken")
        # Allocate above all existing user IDs, including seeded demo accounts.
        # No registration cap or reserved attendee ID range.
        user_id = db.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM users").fetchone()[0]
        db.execute("INSERT INTO users(id,name,points) VALUES(?,?,?)", (user_id, username, PARTICIPANT_START_POINTS))
        db.execute("INSERT INTO accounts(user_id,username,password,is_admin,approved,is_participant) VALUES(?,?,?,?,1,1)",
                   (user_id, username, password_hash, 0))
        db.execute("INSERT INTO transactions(user_id,description,delta,created_at) VALUES(?,?,?,?)",
                   (user_id, "Workshop welcome balance", PARTICIPANT_START_POINTS, now))
    return {"status":"created","message":"Account created. You can sign in immediately."}

@app.post("/api/v1/login")
def login(body: Login):
    with connect() as db:
        acc = db.execute("SELECT user_id,password,approved FROM accounts WHERE username=?", (body.username.strip().lower(),)).fetchone()
        if not acc or not password_matches(body.password, acc["password"]):
            raise HTTPException(401, "Invalid credentials")
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO sessions VALUES(?,?,?)", (token, acc["user_id"], int(time.time())))
        user = db.execute("SELECT id,name,points FROM users WHERE id=?", (acc["user_id"],)).fetchone()
        return {"access_token":token,"token_type":"bearer","user":dict(user)}

@app.get("/api/v1/me")
def me(authorization: Optional[str] = Header(default=None)):
    auth = current_user(authorization)
    with connect() as db:
        return dict(db.execute("SELECT id,name,points FROM users WHERE id=?", (auth["user_id"],)).fetchone())

@app.get("/api/v1/users/{user_id}")
def user_profile(user_id: int, authorization: Optional[str] = Header(default=None)):
    current_user(authorization)
    # INTENTIONAL BOLA: checks authentication but not ownership.
    with connect() as db:
        row = db.execute("SELECT id,name,points FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(404, "User not found")
        return dict(row)

@app.get("/api/v1/users/{user_id}/transactions")
def transactions(user_id: int, authorization: Optional[str] = Header(default=None)):
    current_user(authorization)
    # INTENTIONAL BOLA: cross-account transaction history is accessible.
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT id,user_id,description,delta,created_at FROM transactions WHERE user_id=? ORDER BY id DESC", (user_id,))]

@app.get("/api/v1/rewards")
def rewards():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT id,name,cost FROM rewards ORDER BY id")]

@app.post("/api/v1/redeem")
def redeem(body: Redemption, authorization: Optional[str] = Header(default=None)):
    auth = current_user(authorization)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        reward = db.execute("SELECT id,name,cost FROM rewards WHERE id=?", (body.reward_id,)).fetchone()
        if not reward:
            raise HTTPException(404, "Reward not found")
        cost = body.cost_points if body.cost_points is not None else reward["cost"]
        user = db.execute("SELECT points FROM users WHERE id=?", (auth["user_id"],)).fetchone()
        if user["points"] < cost:
            raise HTTPException(400, "Not enough loyalty points")
        db.execute("UPDATE users SET points=points-? WHERE id=?", (cost,auth["user_id"]))
        now = int(time.time())
        cur = db.execute("INSERT INTO redemptions(user_id,reward_id,charged_points,created_at) VALUES(?,?,?,?)", (auth["user_id"],reward["id"],cost,now))
        db.execute("INSERT INTO transactions(user_id,description,delta,created_at) VALUES(?,?,?,?)", (auth["user_id"],"Redeemed "+reward["name"],-cost,now))
        balance = db.execute("SELECT points FROM users WHERE id=?", (auth["user_id"],)).fetchone()["points"]
        return {"redemption_id":cur.lastrowid,"reward":reward["name"],"charged_points":cost,"remaining_points":balance,"status":"redeemed"}

@app.get("/api/v1/friends")
def friends(authorization: Optional[str] = Header(default=None)):
    auth = current_user(authorization)
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT id,name FROM users WHERE id!=? ORDER BY name", (auth["user_id"],))]

@app.post("/api/v1/transfers")
def transfer_points(body: PointsTransfer, authorization: Optional[str] = Header(default=None)):
    auth = current_user(authorization)
    recipient_name = body.to_user.strip().lower()
    if body.points <= 0 or body.points > 1000000:
        raise HTTPException(400, "Invalid transfer amount")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        target = db.execute("SELECT user_id FROM accounts WHERE username=?", (recipient_name,)).fetchone()
        if not target:
            raise HTTPException(404, "Friend not found")
        if target["user_id"] == auth["user_id"]:
            raise HTTPException(400, "Cannot transfer to yourself")
        now = int(time.time())
        # INTENTIONAL VULNERABILITY: no sender balance check; debt is allowed.
        db.execute("UPDATE users SET points=points-? WHERE id=?", (body.points, auth["user_id"]))
        db.execute("UPDATE users SET points=points+? WHERE id=?", (body.points, target["user_id"]))
        db.execute("INSERT INTO point_transfers(sender_id,recipient_id,amount,created_at) VALUES(?,?,?,?)",
                   (auth["user_id"], target["user_id"], body.points, now))
        db.execute("INSERT INTO transactions(user_id,description,delta,created_at) VALUES(?,?,?,?)",
                   (auth["user_id"], "Sent points to "+recipient_name, -body.points, now))
        db.execute("INSERT INTO transactions(user_id,description,delta,created_at) VALUES(?,?,?,?)",
                   (target["user_id"], "Received points from "+auth["username"], body.points, now))
        balance = db.execute("SELECT points FROM users WHERE id=?", (auth["user_id"],)).fetchone()[0]
    return {"status":"transferred","to_user":recipient_name,"points":body.points,"remaining_points":balance}

@app.post("/api/v1/partner/credit")
def partner_credit(authorization: Optional[str] = Header(default=None),
                   x_mockapp_partner: Optional[str] = Header(default=None)):
    """Workshop-only partner promotion: separate from redemption price tampering."""
    auth = current_user(authorization)
    if not x_mockapp_partner or not hmac.compare_digest(
        x_mockapp_partner, "MOCKAPP-OFFLINE-PROMO-2026"
    ):
        raise HTTPException(403, "Partner promotion denied")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        already = db.execute(
            "SELECT 1 FROM partner_promotions WHERE user_id=?", (auth["user_id"],)
        ).fetchone()
        if already:
            raise HTTPException(409, "Partner promotion has already been used")
        now = int(time.time())
        db.execute("INSERT INTO partner_promotions(user_id,created_at) VALUES(?,?)",
                   (auth["user_id"], now))
        db.execute("UPDATE users SET points=points+10000 WHERE id=?", (auth["user_id"],))
        db.execute(
            "INSERT INTO transactions(user_id,description,delta,created_at) VALUES(?,?,?,?)",
            (auth["user_id"], "Partner promotional credit", 10000, now)
        )
        balance = db.execute("SELECT points FROM users WHERE id=?", (auth["user_id"],)).fetchone()[0]
    return {"status": "credited", "credit": 10000, "remaining_points": balance}

@app.post("/api/v1/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    current_user(authorization)
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE token=?", (authorization[7:],))
    return {"status":"logged_out"}
