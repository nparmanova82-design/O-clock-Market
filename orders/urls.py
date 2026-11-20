from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("savat/", views.cart_detail, name="cart"),
    path("savat/panel/", views.cart_drawer, name="cart_drawer"),
    path("savat/qoshish/<int:pk>/", views.cart_add, name="cart_add"),
    path("savat/tasma/<int:pk>/", views.cart_add_strap, name="cart_add_strap"),
    path("savat/yangilash/<str:key>/", views.cart_update, name="cart_update"),
    path("savat/olib-tashlash/<str:key>/", views.cart_remove, name="cart_remove"),
    path("savat/promokod/", views.promo_apply, name="promo_apply"),
    path("savat/promokod/bekor/", views.promo_remove, name="promo_remove"),
    path("rasmiylashtirish/", views.checkout, name="checkout"),
    path("buyurtma/<str:number>/", views.success, name="success"),
    path("kuzatish/", views.track, name="track"),
    path("qongiroq/", views.callback, name="callback"),
]
