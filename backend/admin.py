"""Home Lab-only portal and reset service. Publish Docker port ONLY on host loopback."""
import os
from pathlib import Path
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from main import connect, initialize, USERS, REWARDS

admin = FastAPI(title="Mockapp Local Lab Settings")
PORTAL = Path(__file__).resolve().parent / "portal"
admin.mount("/assets", StaticFiles(directory=str(PORTAL)), name="assets")
admin.mount("/downloads/files", StaticFiles(directory=str(PORTAL / "downloads")), name="downloads")

@admin.get("/")
def home():
    home_page = PORTAL / "home-lab.html"
    return FileResponse(str(home_page if home_page.exists() else PORTAL / "index.html"))

@admin.get("/setup")
def setup_page():
    return FileResponse(str(PORTAL / "workshop-setup.html"))

@admin.get("/solutions")
def solutions_page():
    return FileResponse(str(PORTAL / "solutions.html"))

@admin.get("/downloads")
def downloads_page():
    return FileResponse(str(PORTAL / "workshop-downloads.html"))

@admin.get("/lab/downloads")
def available_downloads():
    """Only expose presence of known workshop files; do not list arbitrary paths."""
    names = {
        "apk": "app/mockapp-home-lab-v0.5.0-debug.apk",
        "slides": "slides/Mobile_Pentesting_Android_iOS_Workshop.pptx",
        "burp_settings": "burp/mockapp-burp-project-settings.json",
        "burp_certificate": "burp/mockapp-burp.p12",
        "burp_ca": "burp/lab-ca.crt",
        "proxy_gif": "setup/mockapp-proxy-setup.gif",
        "frida_server": "frida/frida-server-17.24.3-android-x86_64.zip",
        "frida_bypass": "frida/bypass-mockapp-pinning.js"
    }
    root = PORTAL / "downloads"
    return {key: (root / relative_path).is_file() for key, relative_path in names.items()}

@admin.get("/lab/health")
def status():
    with connect() as db:
        initialize(db)
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return {"status": "ok", "users": count, "environment": "local"}

@admin.post("/lab/reset")
def reset(request: Request, x_mockapp_lab_reset: str | None = Header(default=None)):
    # The non-secret custom header blocks cross-site form posts and requires CORS preflight.
    origin = request.headers.get("origin")
    if x_mockapp_lab_reset != "reset" or (origin and origin not in ("http://localhost:8080", "http://127.0.0.1:8080")):
        raise HTTPException(403, "Use the local Lab Settings page")
    """Destroy all lab accounts and state, then re-seed. No key on isolated local instance."""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        for table in ("sessions", "transactions", "redemptions", "point_transfers",
                      "partner_promotions", "accounts", "users", "rewards", "workshop_settings"):
            db.execute(f"DELETE FROM {table}")
        initialize(db)
    return {"status": "reset", "sessions_invalidated": True,
            "message": "All accounts and exercise state have been reset"}
