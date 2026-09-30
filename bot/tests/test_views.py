import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from bot.models import Conversa, MensagemRecebida
from core.models import Categoria, Lancamento

TEL = "5567999990000"


def payload(wamid, telefone, texto):
    return {"entry": [{"changes": [{"value": {"messages": [
        {"id": wamid, "from": telefone, "type": "text", "text": {"body": texto}}
    ]}}]}]}


@override_settings(WHATSAPP_VERIFY_TOKEN="segredo123", WHATSAPP_NUMEROS_AUTORIZADOS="")
class WebhookTests(TestCase):
    def setUp(self):
        Categoria.objects.create(nome="Combustível")

    def test_verificacao_com_token_certo(self):
        r = self.client.get(reverse("whatsapp_webhook"), {
            "hub.mode": "subscribe", "hub.verify_token": "segredo123", "hub.challenge": "abc123"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "abc123")

    def test_verificacao_com_token_errado(self):
        r = self.client.get(reverse("whatsapp_webhook"), {
            "hub.mode": "subscribe", "hub.verify_token": "errado", "hub.challenge": "abc"})
        self.assertEqual(r.status_code, 403)

    @patch("bot.views.cliente_padrao.enviar_texto")
    def test_mensagem_cria_conversa_e_responde(self, enviar):
        r = self.client.post(reverse("whatsapp_webhook"), data=json.dumps(payload("wamid.1", TEL, "gasto")),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Conversa.objects.get(telefone=TEL).estado, Conversa.Estado.CATEGORIA)
        enviar.assert_called_once()
        self.assertEqual(enviar.call_args.args[0], TEL)

    @patch("bot.views.cliente_padrao.enviar_texto")
    def test_reenvio_da_meta_nao_processa_duas_vezes(self, enviar):
        for _ in range(2):
            self.client.post(reverse("whatsapp_webhook"), data=json.dumps(payload("wamid.dup", TEL, "gasto")),
                             content_type="application/json")
        self.assertEqual(MensagemRecebida.objects.count(), 1)
        enviar.assert_called_once()

    @override_settings(WHATSAPP_NUMEROS_AUTORIZADOS="5567900000000")
    @patch("bot.views.cliente_padrao.enviar_texto")
    def test_numero_nao_autorizado_e_ignorado(self, enviar):
        self.client.post(reverse("whatsapp_webhook"), data=json.dumps(payload("wamid.x", TEL, "gasto")),
                         content_type="application/json")
        enviar.assert_not_called()
        self.assertEqual(Conversa.objects.filter(telefone=TEL).count(), 0)
        self.assertEqual(MensagemRecebida.objects.count(), 0)

    def test_corpo_invalido_nao_derruba_o_servidor(self):
        r = self.client.post(reverse("whatsapp_webhook"), data="não é json",
                             content_type="application/json")
        self.assertEqual(r.status_code, 400)

    @patch("bot.views.cliente_padrao.enviar_texto")
    def test_fluxo_completo_via_webhook_grava_lancamento(self, enviar):
        passos = ["gasto", "1", "80", "hoje", "1", "sim"]
        for i, texto in enumerate(passos):
            self.client.post(reverse("whatsapp_webhook"), data=json.dumps(payload(f"wamid.{i}", TEL, texto)),
                             content_type="application/json")
        lanc = Lancamento.objects.get()
        self.assertEqual(lanc.valor, Decimal("80.00"))
        self.assertEqual(lanc.origem, "whatsapp")
