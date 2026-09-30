from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from .models import TurnoUber


class TurnoUberTests(SimpleTestCase):
    def test_metricas(self):
        t = TurnoUber(data=date(2026, 3, 1), ganho=Decimal("200.00"), km=Decimal("100.0"), horas=Decimal("8"))
        self.assertEqual(t.ganho_por_hora, Decimal("25.00"))
        self.assertEqual(t.ganho_por_km, Decimal("2.00"))

    def test_sem_divisao_por_zero(self):
        t = TurnoUber(data=date(2026, 3, 1), ganho=Decimal("50"), km=Decimal("0"), horas=Decimal("0"))
        self.assertIsNone(t.ganho_por_hora)
        self.assertIsNone(t.ganho_por_km)
