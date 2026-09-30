from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Categoria, CompraParcelada, Lancamento
from core.services import criar_compra_parcelada


class ParcelasTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nome="Celular")

    def criar(self, **kw):
        base = dict(descricao="Celular", valor_total=Decimal("100.00"), num_parcelas=3,
                    primeira_data=date(2026, 1, 31), categoria=self.cat)
        base.update(kw)
        return criar_compra_parcelada(**base)

    def test_gera_parcelas_com_soma_exata(self):
        compra = self.criar()
        valores = list(compra.lancamentos.order_by("numero_parcela").values_list("valor", flat=True))
        self.assertEqual(valores, [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")])
        self.assertEqual(sum(valores), Decimal("100.00"))

    def test_datas_sem_deriva(self):
        compra = self.criar()
        datas = list(compra.lancamentos.order_by("numero_parcela").values_list("data", flat=True))
        self.assertEqual(datas, [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)])

    def test_parcelas_nascem_pendentes_e_parceladas(self):
        compra = self.criar()
        for p in compra.lancamentos.all():
            self.assertEqual(p.status, Lancamento.Status.PENDENTE)
            self.assertEqual(p.forma, Lancamento.Forma.PARCELADO)
            self.assertEqual(p.tipo, Lancamento.Tipo.SAIDA)

    def test_restante_diminui_ao_pagar(self):
        compra = self.criar()
        self.assertEqual(compra.parcelas_restantes, 3)
        self.assertEqual(compra.valor_restante, Decimal("100.00"))
        primeira = compra.lancamentos.get(numero_parcela=1)
        primeira.status = Lancamento.Status.PAGO
        primeira.save()
        self.assertEqual(compra.parcelas_restantes, 2)
        self.assertEqual(compra.valor_restante, Decimal("66.66"))

    def test_cancelar_parcela_tira_do_restante(self):
        compra = self.criar()
        compra.lancamentos.get(numero_parcela=3).cancelar()
        self.assertEqual(compra.parcelas_restantes, 2)
        self.assertEqual(compra.lancamentos.count(), 3)  # nada é apagado

    def test_numero_de_parcelas_invalido(self):
        for n in (0, 121):
            with self.assertRaises(ValidationError):
                self.criar(num_parcelas=n)
        self.assertEqual(CompraParcelada.objects.count(), 0)

    def test_valor_invalido_nao_grava_nada(self):
        with self.assertRaises(ValidationError):
            self.criar(valor_total=Decimal("0"))
        self.assertEqual(Lancamento.objects.count(), 0)

    def test_mensagem_duplicada_do_whatsapp_e_recusada(self):
        self.criar(mensagem_id="wamid.ABC")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar(mensagem_id="wamid.ABC")
        self.assertEqual(CompraParcelada.objects.count(), 1)
        self.assertEqual(Lancamento.objects.count(), 3)
