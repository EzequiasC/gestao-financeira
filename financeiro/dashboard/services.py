from datetime import date
from decimal import Decimal

from django.db.models import Count, Q, Sum

from core.models import CompraParcelada, Lancamento
from core.utils import add_months
from uber.models import TurnoUber

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _soma(qs):
    return qs.aggregate(t=Sum("valor"))["t"] or ZERO


def _dividir(a, b):
    return (a / b).quantize(CENT) if b else None


def resumo_mes(ano: int, mes: int) -> dict:
    """Todos os números do dashboard de um mês. Lançamentos cancelados nunca entram.

    Entradas = lançamentos de entrada + ganho dos turnos do Uber.
    (Registre o ganho do Uber pelo turno, não como lançamento, para não contar duas vezes.)
    """
    L = Lancamento
    inicio = date(ano, mes, 1)
    fim = add_months(inicio, 1)

    validos = L.objects.filter(data__gte=inicio, data__lt=fim).exclude(status=L.Status.CANCELADO)
    saidas = validos.filter(tipo=L.Tipo.SAIDA)

    # Uber
    t = TurnoUber.objects.filter(data__gte=inicio, data__lt=fim).aggregate(
        ganho=Sum("ganho"), km=Sum("km"), horas=Sum("horas"), n=Count("id"))
    ganho, km, horas = t["ganho"] or ZERO, t["km"] or ZERO, t["horas"] or ZERO
    gastos_uber = _soma(saidas.filter(categoria__uber=True))
    liquido = ganho - gastos_uber
    uber = {
        "turnos": t["n"], "ganho": ganho, "km": km, "horas": horas,
        "gastos": gastos_uber, "liquido": liquido,
        "liquido_por_hora": _dividir(liquido, horas),
        "liquido_por_km": _dividir(liquido, km),
    }

    # Totais do mês
    entradas = _soma(validos.filter(tipo=L.Tipo.ENTRADA)) + ganho
    saidas_total = _soma(saidas)
    a_pagar = _soma(saidas.filter(status=L.Status.PENDENTE))
    saidas_pagas = saidas_total - a_pagar

    # Fixos e parcelas do mês
    fixos = validos.filter(gasto_fixo__isnull=False).select_related("categoria").order_by("data")
    parcelas = validos.filter(compra__isnull=False).select_related("compra").order_by("data")
    pend = Q(lancamentos__status=L.Status.PENDENTE)
    compras_abertas = (CompraParcelada.objects
                       .annotate(restantes=Count("lancamentos", filter=pend),
                                 devendo=Sum("lancamentos__valor", filter=pend))
                       .filter(restantes__gt=0).order_by("descricao"))

    cats = saidas.values("categoria__nome").annotate(total=Sum("valor")).order_by("-total")
    por_categoria = [{
        "nome": c["categoria__nome"], "total": c["total"],
        "pct": int(c["total"] / saidas_total * 100) if saidas_total else 0,
    } for c in cats]

    return {
        "entradas": entradas,
        "saidas_pagas": saidas_pagas,
        "a_pagar": a_pagar,
        "saidas_total": saidas_total,
        "saldo_atual": entradas - saidas_pagas,
        "saldo_previsto": entradas - saidas_total,
        "uber": uber,
        "fixos": fixos,
        "fixos_pendente": _soma(fixos.filter(status=L.Status.PENDENTE)),
        "parcelas": parcelas,
        "parcelas_pendente": _soma(parcelas.filter(status=L.Status.PENDENTE)),
        "compras_abertas": compras_abertas,
        "por_categoria": por_categoria,
        "ultimos": validos.select_related("categoria")[:10],
    }
