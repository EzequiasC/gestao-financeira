import calendar
from datetime import date
from decimal import ROUND_DOWN, Decimal

CENTAVO = Decimal("0.01")


def add_months(d: date, months: int) -> date:
    """Soma meses mantendo o dia, ajustando para o fim do mês (31/01 + 1 = 28/02)."""
    total = d.month - 1 + months
    ano, mes = d.year + total // 12, total % 12 + 1
    return date(ano, mes, min(d.day, calendar.monthrange(ano, mes)[1]))


def dividir_valor(total, n: int) -> list[Decimal]:
    """Divide `total` em `n` partes; a soma é SEMPRE exatamente `total`.
    Centavos que sobram vão para as primeiras parcelas (100,00/3 -> 33,34 + 33,33 + 33,33)."""
    if n < 1:
        raise ValueError("n deve ser >= 1")
    total = Decimal(total).quantize(CENTAVO)
    base = (total / n).quantize(CENTAVO, rounding=ROUND_DOWN)
    valores = [base] * n
    sobra = int((total - base * n) / CENTAVO)
    for i in range(sobra):
        valores[i] += CENTAVO
    return valores
