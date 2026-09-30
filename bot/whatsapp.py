"""Cliente fino para a WhatsApp Cloud API. Isolado num módulo só para poder
trocar por um "fake" nos testes sem tocar na lógica de conversa."""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ClienteWhatsApp:
    def enviar_texto(self, telefone: str, texto: str) -> None:
        token = getattr(settings, "WHATSAPP_TOKEN", "")
        phone_id = getattr(settings, "WHATSAPP_PHONE_ID", "")
        if not token or not phone_id:
            logger.info("[WhatsApp simulado] para %s: %s", telefone, texto)
            return
        url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
        try:
            requests.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json={"messaging_product": "whatsapp", "to": telefone,
                      "type": "text", "text": {"body": texto}},
                timeout=10,
            )
        except requests.RequestException:
            logger.exception("Falha ao enviar mensagem para %s", telefone)


cliente_padrao = ClienteWhatsApp()
