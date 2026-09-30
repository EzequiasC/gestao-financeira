from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from core.utils import add_months, dividir_valor


class AddMonthsTests(SimpleTestCase):
    def test_fim_de_mes_ajusta(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))

    def test_ano_bissexto(self):
        self.assertEqual(add_months(date(2028, 1, 31), 1), date(2028, 2, 29))

    def test_virada_de_ano(self):
        self.assertEqual(add_months(date(2026, 11, 15), 3), date(2027, 2, 15))


class DividirValorTests(SimpleTestCase):
    def test_soma_exata(self):
        partes = dividir_valor("100.00", 3)
        self.assertEqual(partes, [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")])
        self.assertEqual(sum(partes), Decimal("100.00"))

    def test_soma_exata_varios_casos(self):
        for total in ["0.01", "1.00", "99.99", "1234.56", "10000.00"]:
            for n in (1, 2, 3, 7, 12, 48):
                if Decimal(total) < Decimal("0.01") * n:
                    continue
                self.assertEqual(sum(dividir_valor(total, n)), Decimal(total), (total, n))

    def test_n_invalido(self):
        with self.assertRaises(ValueError):
            dividir_valor("10", 0)
