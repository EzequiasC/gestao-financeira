from django.contrib import admin

from .models import Conversa, MensagemRecebida


@admin.register(Conversa)
class ConversaAdmin(admin.ModelAdmin):
    list_display = ("telefone", "estado", "atualizado_em")


@admin.register(MensagemRecebida)
class MensagemRecebidaAdmin(admin.ModelAdmin):
    list_display = ("telefone", "texto", "recebida_em")
    readonly_fields = [f.name for f in MensagemRecebida._meta.fields]

    def has_add_permission(self, request):
        return False
