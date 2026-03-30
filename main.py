from fastapi import FastAPI, HTTPException
from database import insert_url
from utils import generate_short_code
from fastapi import BackgroundTasks, Request
import os
from supabase import create_client
from dotenv import load_dotenv
from cache import get_cached_url, cache_url, delete_cache
from rate_limiter import is_rate_limited
from typing import Optional
from datetime import datetime, timedelta
from fastapi.responses import RedirectResponse
from database import get_url, get_url_record
from database import insert_click
from utils import hash_ip
from fastapi.middleware.cors import CORSMiddleware

MAX_SHORT_CODE_LENGTH = 10
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

app = FastAPI()

@app.post("/shorten")
def shorten_url(
    original_url: str,
    custom_code: Optional[str] = None,
    expiry_minutes: Optional[int] = None,
    request: Request = None
):
    try:
        ip = request.client.host

        if is_rate_limited(ip):
            raise HTTPException(status_code=429, detail="Too many requests")

        # Custom alias
        if custom_code:
            if len(custom_code) > MAX_SHORT_CODE_LENGTH:
                raise HTTPException(
                    status_code=400,
                    detail=f"Custom alias must be at most {MAX_SHORT_CODE_LENGTH} characters long"
                )
            if get_url(custom_code):
                raise HTTPException(status_code=400, detail="Alias taken")
            code = custom_code
        else:
            code = generate_short_code(length=min(6, MAX_SHORT_CODE_LENGTH))
            while get_url(code):
                code = generate_short_code(length=min(6, MAX_SHORT_CODE_LENGTH))

        # 🔥 Expiry logic
        expires_at = None
        if expiry_minutes:
            expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)

        insert_url(code, original_url, expires_at)

        return {
            "short_url": f"{BASE_URL}/{code}",
            "expires_at": expires_at.isoformat() if expires_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/{code}")
def redirect(code: str, request: Request, bg: BackgroundTasks):
    url = None

    # Step 1: Check cache
    cached_value = get_cached_url(code)
    if isinstance(cached_value, dict):
        cached_url = cached_value.get("original_url")
        cached_expires_at = cached_value.get("expires_at")

        if cached_expires_at:
            expires_at = datetime.fromisoformat(cached_expires_at)
            now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.utcnow()
            if now > expires_at:
                delete_cache(code)
            else:
                url = cached_url
        else:
            url = cached_url
    elif isinstance(cached_value, str):
        # Older cache entries only stored the URL, so refresh from DB to enforce expiry.
        url = None

    if url:
        print("HIT")
    else:
        print("MISS")

    # Step 2: Fallback to DB
    if not url:
        record = get_url_record(code)

        if not record:
            delete_cache(code)
            raise HTTPException(status_code=404, detail="URL not found")

        url = record["original_url"]

        # Step 3: Cache it
        expires_at = record.get("expires_at")
        ttl = 86400
        if expires_at:
            expiry_dt = datetime.fromisoformat(expires_at[:-1] + "+00:00") if expires_at.endswith("Z") else datetime.fromisoformat(expires_at)
            now = datetime.now(expiry_dt.tzinfo) if expiry_dt.tzinfo else datetime.utcnow()
            ttl = max(1, int((expiry_dt - now).total_seconds()))

        cache_url(
            code,
            {"original_url": url, "expires_at": expires_at},
            ttl=ttl
        )

    # Step 4: Log click
    bg.add_task(log_click, code, request)
    return RedirectResponse(url, status_code=301)


@app.get("/stats/{code}")
def get_stats(code: str):
    response = supabase.table("clicks") \
        .select("*") \
        .eq("short_code", code) \
        .execute()

    return {
        "total_clicks": len(response.data),
        "data": response.data
    }



def log_click(code: str, request):
    try:
        ip = request.client.host
        ip_hashed = hash_ip(ip)

        data = {
            "short_code": code,
            "ip_hash": ip_hashed,
            "referrer": request.headers.get("referer"),
            "user_agent": request.headers.get("user-agent")
        }

        insert_click(data)
    except Exception as e:
        print("Logging failed:", e)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
