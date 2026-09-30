from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

MIN_VALOR = MinValueValidator(Decimal("0.01"))


def dinheiro(**kw):
    return models.DecimalField(max_digits=12, decimal_places=2, validators=[MIN_VALOR], **kw)


class Origem(models.TextChoices):
    SITE = "site", "Site"
    WHATSAPP = "whatsapp", "WhatsApp"


class Categoria(models.Model):
    nome = models.CharField(max_length=60, unique=True)
    uber = models.BooleanField("relacionada ao Uber", default=False)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class GastoFixo(models.Model):
    descricao = models.CharField(max_length=120)
    valor = dinheiro()
    dia_vencimento = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    inicio = models.DateField("vale a partir de", default=timezone.localdate)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.descricao} (dia {self.dia_vencimento})"


class CompraParcelada(models.Model):
    descricao = models.CharField(max_length=120)
    valor_total = dinheiro()
    num_parcelas = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(120)])
    primeira_data = models.DateField()
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    origem = models.CharField(max_length=10, choices=Origem.choices, default=Origem.SITE)
    mensagem_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.descricao} ({self.num_parcelas}x)"

    def _abertas(self):
        return self.lancamentos.filter(status=Lancamento.Status.PENDENTE)

    @property
    def parcelas_restantes(self) -> int:
        return self._abertas().count()

    @property
    def valor_restante(self) -> Decimal:
        return self._abertas().aggregate(t=Sum("valor"))["t"] or Decimal("0.00")


class Lancamento(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"

    class Forma(models.TextChoices):
        AVISTA = "avista", "À vista"
        PARCELADO = "parcelado", "Parcelado"

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        PAGO = "pago", "Pago"
        CANCELADO = "cancelado", "Cancelado"  # nunca apagamos: cancelamos

    data = models.DateField()
    valor = dinheiro()
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.SAIDA)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    descricao = models.CharField(max_length=160, blank=True)
    forma = models.CharField(max_length=10, choices=Forma.choices, default=Forma.AVISTA)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PAGO)
    origem = models.CharField(max_length=10, choices=Origem.choices, default=Origem.SITE)

    compra = models.ForeignKey(CompraParcelada, null=True, blank=True, on_delete=models.PROTECT,
                               related_name="lancamentos")
    numero_parcela = models.PositiveSmallIntegerField(null=True, blank=True)
    gasto_fixo = models.ForeignKey(GastoFixo, null=True, blank=True, on_delete=models.PROTECT,
                                   related_name="lancamentos")
    competencia = models.DateField("mês de referência", null=True, blank=True)

    # Idempotência: a Meta reenvia webhooks; o mesmo ID nunca grava duas vezes.
    mensagem_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(valor__gt=0), name="lancamento_valor_positivo"),
            models.UniqueConstraint(fields=["compra", "numero_parcela"], name="uniq_parcela_por_compra"),
            models.UniqueConstraint(fields=["gasto_fixo", "competencia"], name="uniq_fixo_por_mes"),
        ]

    def __str__(self):
        return f"{self.data:%d/%m/%Y} {self.descricao or self.categoria} R$ {self.valor}"

    def cancelar(self):
        self.status = self.Status.CANCELADO
        self.save(update_fields=["status", "atualizado_em"])
