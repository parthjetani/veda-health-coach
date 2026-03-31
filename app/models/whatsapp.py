from pydantic import BaseModel, ConfigDict


# -- Incoming webhook payload models (deeply nested Meta structure) --

class WhatsAppText(BaseModel):
    body: str


class WhatsAppImage(BaseModel):
    id: str
    mime_type: str | None = None
    sha256: str | None = None
    caption: str | None = None


class WhatsAppButtonReply(BaseModel):
    id: str
    title: str


class WhatsAppInteractive(BaseModel):
    type: str | None = None
    button_reply: WhatsAppButtonReply | None = None


class WhatsAppMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str | None = None  # sender phone number
    id: str | None = None  # message ID for idempotency
    timestamp: str | None = None
    type: str  # "text", "image", "interactive", etc.
    text: WhatsAppText | None = None
    image: WhatsAppImage | None = None
    interactive: WhatsAppInteractive | None = None

    def __init__(self, **data):
        # Handle "from" being a reserved keyword in Python
        if "from" in data:
            data["from_"] = data.pop("from")
        super().__init__(**data)


class WhatsAppContact(BaseModel):
    wa_id: str | None = None
    profile: dict | None = None


class WhatsAppStatus(BaseModel):
    id: str | None = None
    status: str | None = None  # "delivered", "read", "sent"
    timestamp: str | None = None
    recipient_id: str | None = None


class WhatsAppValue(BaseModel):
    messaging_product: str | None = None
    metadata: dict | None = None
    contacts: list[WhatsAppContact] | None = None
    messages: list[WhatsAppMessage] | None = None
    statuses: list[WhatsAppStatus] | None = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str | None = None


class WhatsAppEntry(BaseModel):
    id: str | None = None
    changes: list[WhatsAppChange]


class WhatsAppWebhook(BaseModel):
    object: str | None = None
    entry: list[WhatsAppEntry]


# -- Helper to extract the first user message from a webhook payload --

def extract_message(payload: WhatsAppWebhook) -> WhatsAppMessage | None:
    for entry in payload.entry:
        for change in entry.changes:
            if change.value.messages:
                return change.value.messages[0]
    return None
