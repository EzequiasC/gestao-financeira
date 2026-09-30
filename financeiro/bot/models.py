from django.db import models


class Conversa(models.Model):
    """Guarda em que ponto da pergunta o número está. Fica no banco (não em memória)
    para sobreviver a reinício do servidor."""

    class Estado(models.TextChoices):
        INICIO = "inicio", "Início"
        CATEGORIA = "categoria", "Aguardando categoria"
        VALOR = "valor", "Aguardando valor"
        DIA = "dia", "Aguardando dia"
        FORMA = "forma", "Aguardando forma (à vista/parcelado)"
        PARCELAS = "parcelas", "Aguardando número de parcelas"
        CONFIRMAR = "confirmar", "Aguardando confirmação"

    telefone = models.CharField(max_length=20, unique=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.INICIO)
    dados = models.JSONField(default=dict, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.telefone} ({self.estado})"

    def reiniciar(self):
        self.estado = self.Estado.INICIO
        self.dados = {}


class MensagemRecebida(models.Model):
    """Todo webhook da Meta traz um ID (wamid). A Meta reenvia se não responder rápido
    ou se der timeout; guardando o ID aqui, nunca processamos a mesma mensagem duas vezes."""
    wamid = models.CharField(max_length=100, unique=True)
    telefone = models.CharField(max_length=20)
    texto = models.CharField(max_length=500, blank=True)
    recebida_em = models.DateTimeField(auto_now_add=True)
