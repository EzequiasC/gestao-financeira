from django.contrib import admin

from .models import TurnoUber


@admin.register(TurnoUber)
class TurnoUberAdmin(admin.ModelAdmin):
    list_display = ("data", "ganho", "km", "horas", "ganho_por_hora", "ganho_por_km")
    date_hierarchy = "data"
