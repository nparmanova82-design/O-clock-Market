from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("", views.home, name="home"),
    path("katalog/", views.catalog, name="catalog"),
    path("aksiya/", views.sale, name="sale"),
    path("unique/", views.unique, name="unique"),
    path("yangi/", views.new_arrivals, name="new"),
    path("brendlar/", views.brands, name="brands"),
    path("brend/<slug:slug>/", views.brand_detail, name="brand"),
    path("soat/<slug:slug>/", views.watch_detail, name="watch"),
    path("tasmalar/", views.straps, name="straps"),
    path("tasma/<slug:slug>/", views.strap_detail, name="strap"),
    path("sevimlilar/", views.wishlist, name="wishlist"),
    path("sevimlilar/<int:pk>/", views.wishlist_toggle, name="wishlist_toggle"),
    path("qidiruv/", views.search_suggest, name="search_suggest"),
    # Ma’lumot sahifalari
    path("yetkazib-berish-va-tolov/", views.info_page("delivery"), name="delivery"),
    path("kafolat-va-qaytarish/", views.info_page("warranty"), name="warranty"),
    path("biz-haqimizda/", views.info_page("about"), name="about"),
    path("aloqa/", views.info_page("contacts"), name="contacts"),
    path("savol-javob/", views.info_page("faq"), name="faq"),
]
