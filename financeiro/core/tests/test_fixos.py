from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Categoria, GastoFixo, Lancamento
from core.services import gerar_fixos_do_mes


class FixosTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nome="Moradia")

    def fixo(self, **kw):
        base = dict(descricao="Aluguel", valor=Decimal("800.00"), dia_vencimento=10,
                    categoria=self.cat, inicio=date(2026, 1, 1))
        base.update(kw)
        return GastoFixo.objects.create(**base)

    def test_gera_lancamento_do_mes(self):
        self.fixo()
        self.assertEqual(gerar_fixos_do_mes(2026, 3), 1)
        l = Lancamento.objects.get()
        self.assertEqual(l.data, date(2026, 3, 10))
        self.assertEqual(l.valor, Decimal("800.00"))
        self.assertEqual(l.status, Lancamento.Status.PENDENTE)

    def test_idempotente(self):
        self.fixo()
        gerar_fixos_do_mes(2026, 3)
        self.assertEqual(gerar_fixos_do_mes(2026, 3), 0)
        self.assertEqual(Lancamento.objects.count(), 1)

    def test_dia_31_em_fevereiro(self):
        self.fixo(dia_vencimento=31)
        gerar_fixos_do_mes(2026, 2)
        self.assertEqual(Lancamento.objects.get().data, date(2026, 2, 28))

    def test_inativo_e_ignorado(self):
        self.fixo(ativo=False)
        self.assertEqual(gerar_fixos_do_mes(2026, 3), 0)

    def test_nao_gera_antes_do_inicio(self):
        self.fixo(inicio=date(2026, 5, 15))
        self.assertEqual(gerar_fixos_do_mes(2026, 4), 0)
        self.assertEqual(gerar_fixos_do_mes(2026, 5), 1)

    def test_alterar_valor_do_fixo_nao_muda_meses_ja_gerados(self):
        f = self.fixo()
        gerar_fixos_do_mes(2026, 3)
        f.valor = Decimal("900.00")
        f.save()
        gerar_fixos_do_mes(2026, 4)
        valores = list(Lancamento.objects.order_by("data").values_list("valor", flat=True))
        self.assertEqual(valores, [Decimal("800.00"), Decimal("900.00")])

    def test_banco_recusa_duplicado_e_valor_zero(self):
        f = self.fixo()
        gerar_fixos_do_mes(2026, 3)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Lancamento.objects.create(data=date(2026, 3, 10), valor=Decimal("1"), categoria=self.cat,
                                      gasto_fixo=f, competencia=date(2026, 3, 1))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Lancamento.objects.create(data=date(2026, 3, 10), valor=Decimal("0"), categoria=self.cat)
