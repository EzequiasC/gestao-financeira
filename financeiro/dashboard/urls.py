from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="dashboard"),
    path("pagar/<int:pk>/", views.marcar_pago, name="marcar_pago"),
]
