from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

ZERO = MinValueValidator(Decimal("0"))


class TurnoUber(models.Model):
    data = models.DateField()
    ganho = models.DecimalField("ganho bruto (R$)", max_digits=10, decimal_places=2, validators=[ZERO])
    km = models.DecimalField(max_digits=8, decimal_places=1, validators=[ZERO])
    horas = models.DecimalField(max_digits=5, decimal_places=2, validators=[ZERO])
    observacao = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-data", "-id"]

    def __str__(self):
        return f"Uber {self.data:%d/%m/%Y} R$ {self.ganho}"

    @property
    def ganho_por_hora(self):
        return (self.ganho / self.horas).quantize(Decimal("0.01")) if self.horas else None

    @property
    def ganho_por_km(self):
        return (self.ganho / self.km).quantize(Decimal("0.01")) if self.km else None
