from fastapi import Header, HTTPException

from app.config import get_settings


async def require_admin_key(x_api_key: str = Header(...)) -> str:
    settings = get_settings()
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key
