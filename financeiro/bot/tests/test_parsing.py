from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from bot.parsing import parse_dia, parse_forma, parse_num_parcelas, parse_valor


class ParseValorTests(SimpleTestCase):
    def test_formatos_comuns(self):
        casos = {"49,90": "49.90", "R$ 49,90": "49.90", "49.90": "49.90",
                 "1.234,56": "1234.56", "50": "50.00", " 10,5 ": "10.50"}
        for entrada, esperado in casos.items():
            self.assertEqual(parse_valor(entrada), Decimal(esperado), entrada)

    def test_invalidos(self):
        for entrada in ("", "abc", "0", "-5", "R$"):
            self.assertIsNone(parse_valor(entrada), entrada)


class ParseDiaTests(SimpleTestCase):
    def setUp(self):
        self.hoje = date(2026, 3, 15)

    def test_relativos(self):
        self.assertEqual(parse_dia("hoje", self.hoje), self.hoje)
        self.assertEqual(parse_dia("HOJE", self.hoje), self.hoje)
        self.assertEqual(parse_dia("ontem", self.hoje), date(2026, 3, 14))

    def test_data_com_e_sem_ano(self):
        self.assertEqual(parse_dia("10/03", self.hoje), date(2026, 3, 10))
        self.assertEqual(parse_dia("10/03/2025", self.hoje), date(2025, 3, 10))
        self.assertEqual(parse_dia("10-03", self.hoje), date(2026, 3, 10))

    def test_invalidos(self):
        for entrada in ("32/01", "10/13", "qualquer coisa", ""):
            self.assertIsNone(parse_dia(entrada, self.hoje), entrada)


class ParseFormaTests(SimpleTestCase):
    def test_avista(self):
        for t in ("1", "avista", "à vista", "a vista"):
            self.assertEqual(parse_forma(t), "avista")

    def test_parcelado(self):
        for t in ("2", "parcelado", "parcela"):
            self.assertEqual(parse_forma(t), "parcelado")

    def test_invalido(self):
        self.assertIsNone(parse_forma("3"))


class ParseNumParcelasTests(SimpleTestCase):
    def test_validos(self):
        self.assertEqual(parse_num_parcelas("12"), 12)
        self.assertEqual(parse_num_parcelas("12x"), 12)

    def test_invalidos(self):
        for t in ("1", "121", "abc", "0"):
            self.assertIsNone(parse_num_parcelas(t))
