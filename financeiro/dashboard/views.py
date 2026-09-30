from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Lancamento
from core.utils import add_months

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

from .services import resumo_mes


def _parse_mes(valor, hoje):
    try:
        ano, mes = (int(x) for x in valor.split("-"))
        date(ano, mes, 1)
        return ano, mes
    except (AttributeError, ValueError):
        return hoje.year, hoje.month


def _chave(d):
    return f"{d.year}-{d.month:02d}"


@login_required
def home(request):
    hoje = timezone.localdate()
    ano, mes = _parse_mes(request.GET.get("mes"), hoje)
    primeiro = date(ano, mes, 1)
    ctx = resumo_mes(ano, mes)
    ctx.update({
        "titulo_mes": f"{MESES[mes - 1]} {ano}",
        "mes_chave": _chave(primeiro),
        "mes_anterior": _chave(add_months(primeiro, -1)),
        "mes_seguinte": _chave(add_months(primeiro, 1)),
        "e_mes_atual": (ano, mes) == (hoje.year, hoje.month),
    })
    return render(request, "dashboard/home.html", ctx)


@login_required
@require_POST
def marcar_pago(request, pk):
    lanc = get_object_or_404(Lancamento, pk=pk)
    if lanc.status == Lancamento.Status.PENDENTE:
        lanc.status = Lancamento.Status.PAGO
        lanc.save(update_fields=["status", "atualizado_em"])
    ano, mes = _parse_mes(request.POST.get("mes"), timezone.localdate())
    return redirect(f"{reverse('dashboard')}?mes={ano}-{mes:02d}")
