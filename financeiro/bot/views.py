import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import MensagemRecebida
from .services import processar_mensagem
from .whatsapp import cliente_padrao

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook(request):
    """Um único endpoint: a Meta faz GET uma vez (verificação) e POST a cada mensagem."""
    if request.method == "GET":
        return verificar_webhook(request)
    if request.method == "POST":
        return receber_webhook(request)
    return HttpResponseNotAllowed(["GET", "POST"])


def verificar_webhook(request):
    """A Meta chama essa URL uma vez, no momento em que você configura o webhook no painel,
    só para confirmar que o servidor é seu."""
    if (request.GET.get("hub.mode") == "subscribe"
            and request.GET.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN):
        return HttpResponse(request.GET.get("hub.challenge", ""), content_type="text/plain")
    return HttpResponseForbidden("token inválido")


def _numeros_autorizados() -> set[str]:
    return {n.strip() for n in settings.WHATSAPP_NUMEROS_AUTORIZADOS.split(",") if n.strip()}


def _extrair_mensagens(payload: dict):
    for entrada in payload.get("entry", []):
        for alteracao in entrada.get("changes", []):
            yield from alteracao.get("value", {}).get("messages", [])


def receber_webhook(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    autorizados = _numeros_autorizados()
    for msg in _extrair_mensagens(payload):
        wamid = msg.get("id")
        telefone = msg.get("from", "")
        texto = msg.get("text", {}).get("body", "")

        if not wamid or MensagemRecebida.objects.filter(wamid=wamid).exists():
            continue  # já processada (reenvio da Meta) — idempotência
        if autorizados and telefone not in autorizados:
            logger.warning("Mensagem recusada: número não autorizado (%s)", telefone)
            continue  # só o(s) seu(s) número(s) pode(m) lançar gastos

        MensagemRecebida.objects.create(wamid=wamid, telefone=telefone, texto=texto[:500])
        resposta = processar_mensagem(telefone, texto)
        cliente_padrao.enviar_texto(telefone, resposta)

    return JsonResponse({"status": "ok"})
