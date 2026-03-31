"""
Daily Health Tips

30 curated tips that rotate daily. Sent via WhatsApp template message
to all active users. Triggered manually via admin endpoint or by cron job.
"""

import logging
from datetime import datetime

from supabase import Client

from app.services.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)

TIPS = [
    "Check your shampoo for 'DMDM Hydantoin' - it releases formaldehyde. Many popular brands use it.",
    "The word 'fragrance' on a label can hide 50+ undisclosed chemicals. Choose fragrance-free when possible.",
    "Sulfate-free shampoos are gentler on your scalp. Look for 'Sodium Cocoyl Isethionate' instead of SLS.",
    "Parabens (methylparaben, propylparaben) are preservatives that may affect hormone balance. Many brands now offer paraben-free options.",
    "Your daily soap touches your entire body. If it has fragrance, that's whole-body chemical exposure every day.",
    "Mineral sunscreens (zinc oxide, titanium dioxide) are safer than chemical ones (oxybenzone, homosalate).",
    "Most mosquito coils release smoke equivalent to 100 cigarettes. Use nets or electric repellents instead.",
    "Store food in glass or steel containers. Heating food in plastic can release chemicals into your meal.",
    "'Natural' on a product label is unregulated - it doesn't guarantee safety. Always check ingredients.",
    "Your toothpaste may contain SLS (Sodium Lauryl Sulfate) which can cause mouth ulcers. SLS-free options exist.",
    "Baby products aren't always gentle. Check for parabens and fragrance even in baby-labeled items.",
    "The fewer ingredients a product has, the less likely it is to cause irritation or contain hidden chemicals.",
    "Deodorants with aluminum compounds block sweat glands. Consider aluminum-free options.",
    "Many 'health drinks' like Bournvita have sugar as the first ingredient. Check labels carefully.",
    "BPA in plastics can mimic estrogen. Look for 'BPA-free' labels on water bottles and food containers.",
    "Air fresheners mask odors with chemicals. Try essential oil diffusers or simply open a window.",
    "Triclosan in antibacterial soaps has been banned in the US. Regular soap and water work just as well.",
    "Instant noodles often contain TBHQ (preservative) and very high sodium. Limit to occasional consumption.",
    "Your dish soap contacts your plates and cups. Residue stays on dishes. Choose gentle, fragrance-free options.",
    "Optical brighteners in detergent stay on clothes and contact your skin all day. Choose fragrance-free detergent.",
    "Palm oil is in many products. While not directly harmful, choose products that use healthier oils when possible.",
    "Artificial food colors (Red 40, Yellow 5) have been linked to hyperactivity in children. Check snack labels.",
    "If you use a product daily, even small amounts of harmful ingredients add up over time. Prioritize daily items.",
    "Simple coconut oil or olive oil can replace many skincare products without any chemical concerns.",
    "Product labels list ingredients by quantity - the first few ingredients make up most of the product.",
    "Lipstick and lip balm get ingested. Check these products extra carefully for harmful ingredients.",
    "High-alcohol mouthwash can dry out your mouth and disrupt oral bacteria. Alcohol-free versions work equally well.",
    "Caramel color in sodas may contain 4-MEI, a potential carcinogen. Choose clear drinks when possible.",
    "Your pillowcase absorbs products from your hair and skin. Wash it frequently, especially if using chemical products.",
    "Type 'my footprint' to see your personal chemical exposure summary based on products you've checked!",
]


def get_daily_tip() -> str:
    day = datetime.now().timetuple().tm_yday  # 1-366
    index = day % len(TIPS)
    return TIPS[index]


async def send_daily_tips(supabase: Client, whatsapp_client: WhatsAppClient) -> int:
    """Send today's health tip to all active users via template message.
    Returns count of users sent to."""

    # Fetch all active users
    result = (
        supabase.table("users")
        .select("whatsapp_number")
        .eq("is_active", True)
        .execute()
    )
    users = result.data or []

    if not users:
        logger.info("No active users for daily tip")
        return 0

    sent = 0
    for user in users:
        number = user.get("whatsapp_number")
        if not number:
            continue
        try:
            # Must use template message (users haven't messaged recently)
            await whatsapp_client.send_template_message(number, "how_to_use")
            sent += 1
        except Exception as e:
            logger.error("Failed to send daily tip to %s: %s", number, e)

    logger.info("Daily tips sent to %d/%d users", sent, len(users))
    return sent
