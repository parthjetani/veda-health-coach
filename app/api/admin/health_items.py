import math

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.footprint import get_user_footprint
from app.core.product_scorer import calculate_score, get_score_label
from app.core.security import require_admin_key
from app.db.queries.analytics import get_analytics
from app.db.queries.feedback import list_feedback
from app.db.queries.health_items import (
    create_health_item,
    delete_health_item,
    get_health_item,
    list_health_items,
    update_health_item,
)
from app.db.queries.unknown_queries import list_unknown_queries
from app.models.admin import HealthItemCreate, HealthItemUpdate, PaginatedResponse

router = APIRouter(dependencies=[Depends(require_admin_key)])


def _enrich_with_score(items: list[dict]) -> list[dict]:
    for item in items:
        score = calculate_score(item)
        item["score"] = score
        item["score_label"] = get_score_label(score)
    return items


@router.get("/health-items", response_model=PaginatedResponse)
async def get_health_items(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    confidence_source: str | None = Query(default=None),
):
    supabase = request.app.state.supabase
    data, total = await list_health_items(
        supabase, page, per_page, category, risk_level, confidence_source
    )
    _enrich_with_score(data)

    return PaginatedResponse(
        data=data,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.post("/health-items", status_code=201)
async def create_item(
    request: Request,
    item: HealthItemCreate,
):
    supabase = request.app.state.supabase
    data = item.model_dump(exclude_unset=True)
    result = await create_health_item(supabase, data)
    _enrich_with_score([result])
    return result


@router.put("/health-items/{item_id}")
async def update_item(
    request: Request,
    item_id: str,
    item: HealthItemUpdate,
):
    supabase = request.app.state.supabase

    existing = await get_health_item(supabase, item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Health item not found")

    data = item.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await update_health_item(supabase, item_id, data)
    if result:
        _enrich_with_score([result])
    return result


@router.delete("/health-items/{item_id}", status_code=204)
async def delete_item(
    request: Request,
    item_id: str,
):
    supabase = request.app.state.supabase

    existing = await get_health_item(supabase, item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Health item not found")

    await delete_health_item(supabase, item_id)
    return None


@router.get("/unknown-queries", response_model=PaginatedResponse)
async def get_unknown_queries(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    supabase = request.app.state.supabase
    data, total = await list_unknown_queries(supabase, page, per_page)

    return PaginatedResponse(
        data=data,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/feedback", response_model=PaginatedResponse)
async def get_feedback(
    request: Request,
    rating: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    supabase = request.app.state.supabase
    data, total = await list_feedback(supabase, rating, page, per_page)

    return PaginatedResponse(
        data=data,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/user-footprint/{user_id}")
async def get_user_footprint_admin(request: Request, user_id: str):
    supabase = request.app.state.supabase
    return await get_user_footprint(supabase, user_id)


@router.get("/analytics")
async def get_dashboard_analytics(request: Request):
    supabase = request.app.state.supabase
    return await get_analytics(supabase)


@router.post("/send-daily-tip")
async def trigger_daily_tip(request: Request):
    from app.config import get_settings
    from app.core.daily_tips import get_daily_tip, send_daily_tips
    from app.services.whatsapp_client import WhatsAppClient

    settings = get_settings()
    supabase = request.app.state.supabase
    whatsapp_client = WhatsAppClient(
        http_client=request.app.state.http_client,
        settings=settings,
    )

    count = await send_daily_tips(supabase, whatsapp_client)
    tip = get_daily_tip()
    return {"sent_to": count, "todays_tip": tip}
