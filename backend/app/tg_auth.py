import hashlib
import hmac
from urllib.parse import parse_qsl

from fastapi import HTTPException

from app.database import settings


def validate_init_data(init_data: str) -> dict:
    if not init_data:
        raise HTTPException(status_code=403, detail="Missing init data")
    data_check_string = "\n".join(
        [f"{k}={v}" for k, v in sorted(parse_qsl(init_data, keep_blank_values=True)) if k != "hash"]
    )
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.get("hash")
    if not received_hash:
        raise HTTPException(status_code=403, detail="Invalid init data")
    secret_key = hashlib.sha256(settings.bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=403, detail="Invalid init data")
    if "user" not in values:
        raise HTTPException(status_code=403, detail="Invalid init data")
    return values
