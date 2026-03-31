from app.models.whatsapp import WhatsAppWebhook, extract_message


class TestWhatsAppWebhookParsing:
    def test_parse_text_message(self, sample_whatsapp_text_payload):
        webhook = WhatsAppWebhook(**sample_whatsapp_text_payload)
        msg = extract_message(webhook)
        assert msg is not None
        assert msg.type == "text"
        assert msg.text.body == "Is Dove soap safe?"
        assert msg.from_ == "16505559876"
        assert msg.id == "wamid.test123"

    def test_parse_image_message(self, sample_whatsapp_image_payload):
        webhook = WhatsAppWebhook(**sample_whatsapp_image_payload)
        msg = extract_message(webhook)
        assert msg is not None
        assert msg.type == "image"
        assert msg.image.id == "media_id_123"
        assert msg.image.mime_type == "image/jpeg"
        assert msg.image.caption == "Check this product"

    def test_status_update_returns_none(self, sample_whatsapp_status_payload):
        webhook = WhatsAppWebhook(**sample_whatsapp_status_payload)
        msg = extract_message(webhook)
        assert msg is None

    def test_empty_entry(self):
        payload = {"object": "whatsapp_business_account", "entry": []}
        webhook = WhatsAppWebhook(**payload)
        msg = extract_message(webhook)
        assert msg is None
