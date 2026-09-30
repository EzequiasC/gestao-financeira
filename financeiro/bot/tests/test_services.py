from decimal import Decimal

from django.test import TestCase

from bot.models import Conversa
from bot.services import processar_mensagem
from core.models import Categoria, CompraParcelada, Lancamento

TEL = "5567999990000"


class FluxoConversaTests(TestCase):
    def setUp(self):
        Categoria.objects.create(nome="Combustível")
        Categoria.objects.create(nome="Mercado")

    def test_fluxo_completo_avista(self):
        self.assertIn("gasto", processar_mensagem(TEL, "oi").lower())
        r = processar_mensagem(TEL, "gasto")
        self.assertIn("Combustível", r)
        self.assertIn("Mercado", r)
        processar_mensagem(TEL, "1")  # Combustível
        processar_mensagem(TEL, "150")
        processar_mensagem(TEL, "hoje")
        r = processar_mensagem(TEL, "1")  # à vista
        self.assertIn("Confirma?", r)
        r = processar_mensagem(TEL, "sim")
        self.assertIn("✅", r)

        lanc = Lancamento.objects.get()
        self.assertEqual(lanc.valor, Decimal("150.00"))
        self.assertEqual(lanc.categoria.nome, "Combustível")
        self.assertEqual(lanc.status, Lancamento.Status.PAGO)
        self.assertEqual(lanc.origem, "whatsapp")

        # conversa reinicia sozinha depois de confirmar
        self.assertEqual(Conversa.objects.get(telefone=TEL).estado, Conversa.Estado.INICIO)

    def test_fluxo_completo_parcelado(self):
        processar_mensagem(TEL, "gasto")
        processar_mensagem(TEL, "2")  # Mercado
        processar_mensagem(TEL, "300")
        processar_mensagem(TEL, "hoje")
        processar_mensagem(TEL, "2")  # parcelado
        r = processar_mensagem(TEL, "3")  # 3x
        self.assertIn("Confirma?", r)
        processar_mensagem(TEL, "sim")

        compra = CompraParcelada.objects.get()
        self.assertEqual(compra.num_parcelas, 3)
        self.assertEqual(compra.lancamentos.count(), 3)
        self.assertEqual(sum(compra.lancamentos.values_list("valor", flat=True)), Decimal("300.00"))

    def test_cancelar_no_meio(self):
        processar_mensagem(TEL, "gasto")
        processar_mensagem(TEL, "1")
        r = processar_mensagem(TEL, "cancelar")
        self.assertIn("cancelei", r.lower())
        self.assertEqual(Conversa.objects.get(telefone=TEL).estado, Conversa.Estado.INICIO)
        self.assertEqual(Lancamento.objects.count(), 0)

    def test_nao_confirmar_nao_grava(self):
        processar_mensagem(TEL, "gasto")
        processar_mensagem(TEL, "1")
        processar_mensagem(TEL, "50")
        processar_mensagem(TEL, "hoje")
        processar_mensagem(TEL, "1")
        processar_mensagem(TEL, "não")
        self.assertEqual(Lancamento.objects.count(), 0)
        self.assertEqual(Conversa.objects.get(telefone=TEL).estado, Conversa.Estado.INICIO)

    def test_entrada_invalida_repete_pergunta_sem_travar(self):
        processar_mensagem(TEL, "gasto")
        processar_mensagem(TEL, "1")
        r = processar_mensagem(TEL, "não é um número")
        self.assertIn("inválido", r.lower())
        self.assertEqual(Conversa.objects.get(telefone=TEL).estado, Conversa.Estado.VALOR)

    def test_categoria_fora_do_intervalo(self):
        processar_mensagem(TEL, "gasto")
        r = processar_mensagem(TEL, "99")
        self.assertIn("não entendi", r.lower())
        self.assertEqual(Conversa.objects.get(telefone=TEL).estado, Conversa.Estado.CATEGORIA)

    def test_duas_pessoas_conversam_ao_mesmo_tempo_sem_se_misturar(self):
        outro = "5567988880000"
        processar_mensagem(TEL, "gasto")
        processar_mensagem(TEL, "1")
        processar_mensagem(outro, "gasto")
        processar_mensagem(TEL, "77")
        self.assertEqual(Conversa.objects.get(telefone=TEL).dados["valor"], "77.00")
        self.assertEqual(Conversa.objects.get(telefone=outro).estado, Conversa.Estado.CATEGORIA)

    def test_sem_categorias_cadastradas_nao_quebra(self):
        Categoria.objects.all().delete()
        r = processar_mensagem("5567900000000", "gasto")
        self.assertIn("categorias", r.lower())
