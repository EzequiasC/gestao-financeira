import calendar
from datetime import date

from django.db import transaction

from .models import CompraParcelada, GastoFixo, Lancamento, Origem
from .utils import add_months, dividir_valor


@transaction.atomic
def criar_compra_parcelada(*, descricao, valor_total, num_parcelas, primeira_data, categoria,
                           origem=Origem.SITE, mensagem_id=None) -> CompraParcelada:
    """Cria a compra e TODAS as parcelas ou nada (transação atômica)."""
    compra = CompraParcelada(descricao=descricao, valor_total=valor_total, num_parcelas=num_parcelas,
                             primeira_data=primeira_data, categoria=categoria, origem=origem,
                             mensagem_id=mensagem_id)
    compra.full_clean(exclude=["mensagem_id"])
    compra.save()
    valores = dividir_valor(valor_total, num_parcelas)
    Lancamento.objects.bulk_create([
        Lancamento(
            data=add_months(primeira_data, i),  # sempre a partir da data original: sem deriva de dia
            valor=valor,
            tipo=Lancamento.Tipo.SAIDA,
            categoria=categoria,
            descricao=f"{descricao} ({i + 1}/{num_parcelas})",
            forma=Lancamento.Forma.PARCELADO,
            status=Lancamento.Status.PENDENTE,
            origem=origem,
            compra=compra,
            numero_parcela=i + 1,
        )
        for i, valor in enumerate(valores)
    ])
    return compra


def gerar_fixos_do_mes(ano: int, mes: int) -> int:
    """Gera os fixos ativos do mês. Pode rodar quantas vezes quiser: nunca duplica."""
    competencia = date(ano, mes, 1)
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    criados = 0
    for fixo in GastoFixo.objects.filter(ativo=True).select_related("categoria"):
        if competencia < fixo.inicio.replace(day=1):
            continue
        _, criado = Lancamento.objects.get_or_create(
            gasto_fixo=fixo, competencia=competencia,
            defaults=dict(
                data=date(ano, mes, min(fixo.dia_vencimento, ultimo_dia)),
                valor=fixo.valor, tipo=Lancamento.Tipo.SAIDA, categoria=fixo.categoria,
                descricao=fixo.descricao, forma=Lancamento.Forma.AVISTA,
                status=Lancamento.Status.PENDENTE,
            ),
        )
        criados += criado
    return criados
