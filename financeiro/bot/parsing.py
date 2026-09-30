"""Interpretação do texto digitado. Tudo aqui é puro (sem banco, sem rede) para ser
fácil de testar. Aceita formatos comuns de brasileiro: vírgula decimal, 'R$', 'hoje'/'ontem'."""
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation


def parse_valor(texto: str) -> Decimal | None:
    texto = texto.strip().lower().replace("r$", "").strip()
    if texto.startswith("-"):
        return None
    texto = texto.replace(".", "").replace(",", ".") if "," in texto else texto
    texto = re.sub(r"[^0-9.]", "", texto)
    if not texto:
        return None
    try:
        valor = Decimal(texto).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    return valor if valor > 0 else None


def parse_dia(texto: str, hoje: date | None = None) -> date | None:
    hoje = hoje or date.today()
    t = texto.strip().lower()
    if t in ("hoje", "hj"):
        return hoje
    if t == "ontem":
        return hoje - timedelta(days=1)
    m = re.fullmatch(r"(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?", t)
    if not m:
        return None
    dia, mes = int(m.group(1)), int(m.group(2))
    ano = int(m.group(3)) if m.group(3) else hoje.year
    if ano < 100:
        ano += 2000
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def parse_forma(texto: str) -> str | None:
    t = texto.strip().lower()
    if t in ("1", "avista", "à vista", "a vista", "vista"):
        return "avista"
    if t in ("2", "parcelado", "parcela", "parcelas"):
        return "parcelado"
    return None


def parse_num_parcelas(texto: str) -> int | None:
    t = texto.strip().lower().rstrip("x")
    if t.isdigit() and 2 <= int(t) <= 120:
        return int(t)
    return None
