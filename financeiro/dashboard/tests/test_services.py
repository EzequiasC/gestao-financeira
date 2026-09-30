from datetime import date
from decimal import Decimal

from django.test import TestCase

from core.models import Categoria, GastoFixo, Lancamento
from core.services import criar_compra_parcelada, gerar_fixos_do_mes
from dashboard.services import resumo_mes
from uber.models import TurnoUber

D = Decimal


class ResumoMesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.salario = Categoria.objects.create(nome="Salário")
        cls.comb = Categoria.objects.create(nome="Combustível", uber=True)
        cls.moradia = Categoria.objects.create(nome="Moradia")
        L = Lancamento
        L.objects.create(data=date(2026, 3, 5), valor=D("500"), tipo=L.Tipo.ENTRADA, categoria=cls.salario)
        L.objects.create(data=date(2026, 3, 6), valor=D("50"), categoria=cls.comb)  # pago, do carro
        L.objects.create(data=date(2026, 3, 7), valor=D("999"), categoria=cls.moradia,
                         status=L.Status.CANCELADO)  # ignorado
        L.objects.create(data=date(2026, 4, 2), valor=D("70"), categoria=cls.comb)  # outro mês
        TurnoUber.objects.create(data=date(2026, 3, 8), ganho=D("200"), km=D("100"), horas=D("8"))
        TurnoUber.objects.create(data=date(2026, 4, 8), ganho=D("100"), km=D("10"), horas=D("1"))
        GastoFixo.objects.create(descricao="Aluguel", valor=D("800"), dia_vencimento=10,
                                 categoria=cls.moradia, inicio=date(2026, 1, 1))
        gerar_fixos_do_mes(2026, 3)
        criar_compra_parcelada(descricao="Celular", valor_total=D("300"), num_parcelas=3,
                               primeira_data=date(2026, 3, 15), categoria=cls.moradia)

    def test_totais(self):
        r = resumo_mes(2026, 3)
        self.assertEqual(r["entradas"], D("700.00"))       # 500 + 200 do Uber
        self.assertEqual(r["saidas_pagas"], D("50.00"))
        self.assertEqual(r["a_pagar"], D("900.00"))         # aluguel 800 + parcela 100
        self.assertEqual(r["saidas_total"], D("950.00"))
        self.assertEqual(r["saldo_atual"], D("650.00"))
        self.assertEqual(r["saldo_previsto"], D("-250.00"))

    def test_uber(self):
        u = resumo_mes(2026, 3)["uber"]
        self.assertEqual(u["ganho"], D("200.00"))
        self.assertEqual(u["gastos"], D("50.00"))
        self.assertEqual(u["liquido"], D("150.00"))
        self.assertEqual(u["liquido_por_hora"], D("18.75"))
        self.assertEqual(u["liquido_por_km"], D("1.50"))
        self.assertEqual(u["turnos"], 1)

    def test_fixos_e_parcelas(self):
        r = resumo_mes(2026, 3)
        self.assertEqual(r["fixos_pendente"], D("800.00"))
        self.assertEqual(r["parcelas_pendente"], D("100.00"))
        compra = r["compras_abertas"].get()
        self.assertEqual((compra.restantes, compra.devendo), (3, D("300.00")))

    def test_categorias_somam_o_total(self):
        r = resumo_mes(2026, 3)
        self.assertEqual(sum(c["total"] for c in r["por_categoria"]), r["saidas_total"])

    def test_mes_vazio_nao_quebra(self):
        r = resumo_mes(2030, 1)
        self.assertEqual(r["saldo_previsto"], D("0.00"))
        self.assertIsNone(r["uber"]["liquido_por_hora"])
        self.assertEqual(r["por_categoria"], [])

    def test_pagar_atualiza_totais(self):
        Lancamento.objects.filter(gasto_fixo__isnull=False).update(status=Lancamento.Status.PAGO)
        r = resumo_mes(2026, 3)
        self.assertEqual(r["a_pagar"], D("100.00"))
        self.assertEqual(r["saldo_previsto"], D("-250.00"))  # previsto não muda ao pagar
        self.assertEqual(r["saldo_atual"], D("-150.00"))     # atual cai
