from django.contrib import admin

from .models import Categoria, CompraParcelada, GastoFixo, Lancamento


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "uber", "ativa")


@admin.register(GastoFixo)
class GastoFixoAdmin(admin.ModelAdmin):
    list_display = ("descricao", "valor", "dia_vencimento", "categoria", "ativo")


@admin.register(CompraParcelada)
class CompraParceladaAdmin(admin.ModelAdmin):
    list_display = ("descricao", "valor_total", "num_parcelas", "parcelas_restantes", "valor_restante")
    readonly_fields = ("origem", "mensagem_id")


@admin.register(Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ("data", "descricao", "valor", "tipo", "categoria", "forma", "status", "origem")
    list_filter = ("tipo", "status", "forma", "origem", "categoria")
    date_hierarchy = "data"
    actions = ["cancelar_selecionados"]

    def has_delete_permission(self, request, obj=None):
        return False  # histórico é sagrado: cancele em vez de apagar

    @admin.action(description="Cancelar lançamentos selecionados")
    def cancelar_selecionados(self, request, queryset):
        queryset.update(status=Lancamento.Status.CANCELADO)
