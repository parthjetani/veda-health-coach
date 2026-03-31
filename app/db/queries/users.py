import logging

from supabase import Client

logger = logging.getLogger(__name__)


async def get_user_by_whatsapp(supabase: Client, whatsapp_number: str) -> dict | None:
    result = (
        supabase.table("users")
        .select("*")
        .eq("whatsapp_number", whatsapp_number)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


async def get_or_create_user(supabase: Client, whatsapp_number: str) -> dict:
    user = await get_user_by_whatsapp(supabase, whatsapp_number)
    if user:
        return user

    result = (
        supabase.table("users")
        .insert({"whatsapp_number": whatsapp_number})
        .execute()
    )
    logger.info("Created new user for %s", whatsapp_number)
    return result.data[0]


async def update_last_active(supabase: Client, user_id: str) -> None:
    try:
        supabase.table("users").update({"last_active_at": "now()"}).eq("id", user_id).execute()
    except Exception as e:
        logger.error("Failed to update last_active_at for %s: %s", user_id, e)


async def activate_user(
    supabase: Client,
    stripe_customer_id: str,
    whatsapp_number: str,
) -> dict | None:
    # Try to find existing user by phone number
    user = await get_user_by_whatsapp(supabase, whatsapp_number)

    if user:
        result = (
            supabase.table("users")
            .update({"is_active": True, "stripe_customer_id": stripe_customer_id})
            .eq("id", user["id"])
            .execute()
        )
        logger.info("Activated user %s (stripe: %s)", whatsapp_number, stripe_customer_id)
        return result.data[0] if result.data else None
    else:
        # User hasn't messaged yet — create and activate
        result = (
            supabase.table("users")
            .insert({
                "whatsapp_number": whatsapp_number,
                "stripe_customer_id": stripe_customer_id,
                "is_active": True,
            })
            .execute()
        )
        logger.info("Created and activated user %s (stripe: %s)", whatsapp_number, stripe_customer_id)
        return result.data[0] if result.data else None


async def deactivate_user(supabase: Client, stripe_customer_id: str) -> bool:
    result = (
        supabase.table("users")
        .update({"is_active": False})
        .eq("stripe_customer_id", stripe_customer_id)
        .execute()
    )
    if result.data:
        logger.info("Deactivated user with stripe_customer_id %s", stripe_customer_id)
        return True
    logger.warning("No user found for stripe_customer_id %s", stripe_customer_id)
    return False


async def list_users(
    supabase: Client,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict], int]:
    offset = (page - 1) * per_page

    # Get total count
    count_result = (
        supabase.table("users")
        .select("id", count="exact")
        .execute()
    )
    total = count_result.count or 0

    # Get paginated results
    result = (
        supabase.table("users")
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    return result.data or [], total
