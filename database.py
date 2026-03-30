import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def _serialize_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value

def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)

def insert_url(short_code, original_url, expires_at=None):
    data = {
        "short_code": short_code,
        "original_url": original_url,
        "expires_at": _serialize_datetime(expires_at)
    }
    supabase.table("urls").insert(data).execute()


def get_url_record(short_code):
    response = supabase.table("urls") \
        .select("*") \
        .eq("short_code", short_code) \
        .execute()

    if response.data:
        record = response.data[0]

        # 🔥 Expiry check
        if record["expires_at"]:
            expires_at = _parse_datetime(record["expires_at"])
            now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.utcnow()

            if now > expires_at:
                return None  # expired

        return record

    return None

def get_url(short_code):
    record = get_url_record(short_code)
    if not record:
        return None
    return record["original_url"]

def insert_click(data):
    supabase.table("clicks").insert(data).execute()

