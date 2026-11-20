"""Chizilgan rasmlar tilga bog‘liq emas — bitta manzildan beriladi va bir marta keshlanadi."""
from django.urls import path

from . import views

app_name = "art"

urlpatterns = [
    path("soat/<slug:slug>/rasm.svg", views.watch_svg, name="watch_svg"),
    path("tasma/<slug:slug>/rasm.svg", views.strap_svg, name="strap_svg"),
    path("rasm/turi/<slug:slug>.svg", views.category_svg, name="category_svg"),
]
