from django.core.management.base import BaseCommand
from django.utils import timezone

from core.services import gerar_fixos_do_mes


class Command(BaseCommand):
    help = "Gera os gastos fixos do mês (padrão: mês atual). Use no cron."

    def add_arguments(self, parser):
        parser.add_argument("--ano", type=int)
        parser.add_argument("--mes", type=int)

    def handle(self, *args, **opts):
        hoje = timezone.localdate()
        ano, mes = opts["ano"] or hoje.year, opts["mes"] or hoje.month
        n = gerar_fixos_do_mes(ano, mes)
        self.stdout.write(f"{n} lançamento(s) criado(s) para {mes:02d}/{ano}.")
