"""Qidiruv tizimlari uchun tuzilgan ma’lumotlar (schema.org JSON-LD).

Google va Yandex shu ma’lumotlardan narx, mavjudlik, brend va «non kesimlari»ni (breadcrumbs)
qidiruv natijasida ko‘rsatadi. Ma’lumot sahifadagi matn bilan bir xil bo‘lishi kerak.
"""
import json

from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import get_language, gettext as _

from .utils import sale_ends_at

_ESCAPES = {ord("<"): "\\u003C", ord(">"): "\\u003E", ord("&"): "\\u0026"}
GENDERS = {"men": "male", "women": "female", "unique": "unisex"}


def script(request, *nodes):
    """Bir nechta schema.org obyektini bitta <script type="application/ld+json"> ga yig‘adi."""
    data = {"@context": "https://schema.org", "@graph": [n for n in nodes if n]}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).translate(_ESCAPES)
    return mark_safe(f'<script type="application/ld+json">{payload}</script>')


def _abs(request, path):
    return request.build_absolute_uri(path)


def store(request):
    s = settings.SHOP
    return {
        "@type": "Store",
        "@id": _abs(request, "/#store"),
        "name": s["name"],
        "url": _abs(request, "/"),
        "logo": _abs(request, static("img/favicon.svg")),
        "image": _abs(request, static("img/favicon.svg")),
        "telephone": s["phone_raw"],
        "email": s["email"],
        "address": {"@type": "PostalAddress", "streetAddress": s["address"], "addressLocality": "Toshkent",
                    "addressCountry": "UZ"},
        "openingHours": s.get("opening_hours", "Mo-Su 09:00-21:00"),
        "currenciesAccepted": "UZS",
        "paymentAccepted": ", ".join(["Naqd pul"] + list(s["cards"])),
        "areaServed": {"@type": "Country", "name": _("O‘zbekiston")},
        "sameAs": [s["telegram"], s["instagram"]],
    }


def website(request):
    return {
        "@type": "WebSite",
        "@id": _abs(request, "/#website"),
        "url": _abs(request, "/"),
        "name": settings.SHOP["name"],
        "inLanguage": (get_language() or "uz")[:2],
        "publisher": {"@id": _abs(request, "/#store")},
        "potentialAction": {
            "@type": "SearchAction",
            "target": {"@type": "EntryPoint",
                       "urlTemplate": _abs(request, reverse("shop:catalog")) + "?q={search_term_string}"},
            "query-input": "required name=search_term_string",
        },
    }


def breadcrumbs(request, items):
    """items: [(nomi, yo‘l yoki None)] — oxirgisi joriy sahifa."""
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, **({"item": _abs(request, url)} if url else {})}
            for i, (name, url) in enumerate(items, 1)
        ],
    }


def product(request, item):
    """Soat yoki tasma uchun Product + Offer."""
    s = settings.SHOP
    watch = item
    url = _abs(request, item.get_absolute_url())
    offer = {
        "@type": "Offer",
        "url": url,
        "price": watch.price,
        "priceCurrency": "UZS",
        "availability": "https://schema.org/" + ("InStock" if watch.in_stock else "OutOfStock"),
        "itemCondition": "https://schema.org/NewCondition",
        "seller": {"@id": _abs(request, "/#store")},
        "shippingDetails": {
            "@type": "OfferShippingDetails",
            "shippingRate": {"@type": "MonetaryAmount", "value": 0, "currency": "UZS"},
            "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "UZ"},
            "deliveryTime": {
                "@type": "ShippingDeliveryTime",
                "handlingTime": {"@type": "QuantitativeValue", "minValue": 0, "maxValue": 1, "unitCode": "DAY"},
                "transitTime": {"@type": "QuantitativeValue", "minValue": 1, "maxValue": 4, "unitCode": "DAY"},
            },
        },
        "hasMerchantReturnPolicy": {
            "@type": "MerchantReturnPolicy",
            "applicableCountry": "UZ",
            "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
            "merchantReturnDays": s["return_days"],
            "returnFees": "https://schema.org/FreeReturn",
        },
    }
    if watch.is_sale:
        offer["priceValidUntil"] = sale_ends_at().date().isoformat()
        offer["priceSpecification"] = [
            {"@type": "UnitPriceSpecification", "price": watch.price, "priceCurrency": "UZS"},
            {"@type": "UnitPriceSpecification", "priceType": "https://schema.org/StrikethroughPrice",
             "price": watch.old_price, "priceCurrency": "UZS"},
        ]
    data = {
        "@type": "Product",
        "@id": url + "#product",
        "name": str(item),
        "url": url,
        "image": [_abs(request, item.image_url)],
        "description": item.local_description or item.short_specs(),
        "sku": item.sku or None,
        "brand": {"@type": "Brand", "name": item.brand.name},
        "offers": offer,
    }
    if item.kind == "watch":
        data.update({
            "category": watch.category.local_name,
            "color": str(watch.get_dial_color_display()),
            "material": str(watch.get_case_material_display()),
            "additionalProperty": [
                {"@type": "PropertyValue", "name": _("Mexanizm"), "value": str(watch.get_mechanism_display())},
                {"@type": "PropertyValue", "name": _("Korpus diametri"), "value": watch.case_size,
                 "unitCode": "MMT"},
                {"@type": "PropertyValue", "name": _("Suvga chidamlilik"), "value": watch.water_resistance,
                 "unitCode": "MTR"},
                {"@type": "PropertyValue", "name": _("Kafolat"), "value": watch.warranty_months, "unitCode": "MON"},
            ],
        })
        if watch.gender in GENDERS:
            data["audience"] = {"@type": "PeopleAudience", "suggestedGender": GENDERS[watch.gender]}
    else:
        data.update({
            "category": _("Soat tasmasi"),
            "color": str(item.get_color_display()),
            "material": str(item.get_material_display()),
            "additionalProperty": [
                {"@type": "PropertyValue", "name": _("Ulanishi"), "value": item.fit_label()},
                {"@type": "PropertyValue", "name": _("Qulf"), "value": str(item.get_buckle_display())},
            ],
        })
    return {k: v for k, v in data.items() if v is not None}
