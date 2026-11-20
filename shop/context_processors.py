from django.conf import settings
from django.db.models import Count, Q
from django.urls import reverse, translate_url
from django.utils.translation import get_language, gettext as _, gettext_noop

from orders.cart import Cart

from .models import Category
from .session_lists import Wishlist
from .utils import sale_ends_at
from .watch_art import ART_VERSION

OG_LOCALES = {"uz": "uz_UZ", "ru": "ru_RU", "en": "en_US"}
# settings.SHOP dagi tarjima qilinadigan matnlar (qiymatlari o‘zbekcha; tarjimasi locale/ da)
SHOP_TEXTS = ("tagline", "address", "hours")
gettext_noop("Har bir daqiqa uchun soat")
gettext_noop("Toshkent sh., Yunusobod tumani, Amir Temur ko‘chasi, 108")
gettext_noop("Har kuni 09:00 — 21:00")


def _site():
    site = dict(settings.SHOP)
    for key in SHOP_TEXTS:
        site[key] = _(site[key])
    return site


def _languages(request, current):
    """Bayroqchalar uchun: shu sahifaning har bir tildagi manzili (so‘rov parametrlari saqlanadi)."""
    path = request.get_full_path()
    return [{"code": code, "name": name, "url": translate_url(path, code), "active": code == current}
            for code, name in settings.LANGUAGES]


def _js_texts():
    """main.js dagi matnlar: sahifaga JSON ko‘rinishida qo‘yiladi."""
    return {
        "cart": _("Savatcha"),
        "view": _("Ko‘rish"),
        "collapse": _("Yig‘ish"),
        "units": [_("kun"), _("soat"), _("daqiqa"), _("soniya")],
        "cartError": _("Savatchani yuklab bo‘lmadi."),
        "cartPage": _("Savatcha sahifasi"),
        "notFound": _("«%(q)s» bo‘yicha hech narsa topilmadi. Brend yoki soat turini yozib ko‘ring."),
        "allResults": _("Barcha soatlar: %(n)s"),
        "strapResults": _("Tasmalar: %(n)s"),
        "urls": {
            "cart": reverse("orders:cart"),
            "wishlist": reverse("shop:wishlist"),
            "catalog": reverse("shop:catalog"),
        },
    }


def shop(request):
    wishlist = Wishlist(request)
    current = (get_language() or settings.LANGUAGE_CODE)[:2]
    return {
        "site": _site(),
        "cart_count": len(Cart(request)),
        "wishlist_ids": wishlist.ids,
        "wishlist_count": len(wishlist),
        "nav_categories": Category.objects.annotate(
            n=Count("watches", filter=Q(watches__is_active=True))),
        "sale_ends": sale_ends_at(),
        "art_version": ART_VERSION,
        "languages": _languages(request, current),
        "og_locale": OG_LOCALES.get(current, "uz_UZ"),
        "js_texts": _js_texts(),
    }
