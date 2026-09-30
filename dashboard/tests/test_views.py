from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Categoria, Lancamento


class ViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("eu", password="senha-bem-longa-123")
        cat = Categoria.objects.create(nome="Moradia")
        self.l = Lancamento.objects.create(data=date(2026, 3, 10), valor=Decimal("800"), categoria=cat,
                                           descricao="Aluguel", status=Lancamento.Status.PENDENTE)

    def test_exige_login(self):
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/contas/login/", r["Location"])

    def test_painel_renderiza(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("dashboard"), {"mes": "2026-03"})
        self.assertContains(r, "Março 2026")
        self.assertContains(r, "Aluguel")
        self.assertContains(r, "800,00")

    def test_mes_invalido_cai_no_mes_atual(self):
        self.client.force_login(self.user)
        for lixo in ("abc", "2026-13", "", "1-2-3"):
            self.assertEqual(self.client.get(reverse("dashboard"), {"mes": lixo}).status_code, 200)

    def test_marcar_pago(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse("marcar_pago", args=[self.l.pk]), {"mes": "2026-03"})
        self.assertRedirects(r, reverse("dashboard") + "?mes=2026-03")
        self.l.refresh_from_db()
        self.assertEqual(self.l.status, Lancamento.Status.PAGO)

    def test_marcar_pago_so_por_post_e_logado(self):
        self.assertEqual(self.client.post(reverse("marcar_pago", args=[self.l.pk])).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("marcar_pago", args=[self.l.pk])).status_code, 405)

    def test_nao_paga_cancelado(self):
        self.l.cancelar()
        self.client.force_login(self.user)
        self.client.post(reverse("marcar_pago", args=[self.l.pk]))
        self.l.refresh_from_db()
        self.assertEqual(self.l.status, Lancamento.Status.CANCELADO)

    def test_login_page(self):
        self.assertContains(self.client.get(reverse("login")), "Entrar")
