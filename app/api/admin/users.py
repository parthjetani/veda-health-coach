import math

from fastapi import APIRouter, Depends, Query, Request

from app.core.security import require_admin_key
from app.db.queries.users import list_users
from app.models.admin import PaginatedResponse

router = APIRouter(dependencies=[Depends(require_admin_key)])


@router.get("/users", response_model=PaginatedResponse)
async def get_users(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    supabase = request.app.state.supabase
    data, total = await list_users(supabase, page, per_page)

    return PaginatedResponse(
        data=data,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )
