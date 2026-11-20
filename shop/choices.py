"""Katalogdagi tanlov ro‘yxatlari: modelda, filtrda va soat rasmini chizishda bir xil ishlatiladi.

Saytda ko‘rinadigan nomlar gettext_lazy bilan o‘ralgan — tanlangan tilga (uz/ru/en) qarab tarjima qilinadi.
Faqat admin paneldagi rasm sozlamalari (korpus shakli, bezel va h.k.) o‘zbekcha qoldirilgan.
"""
from django.utils.translation import gettext, gettext_lazy as _

GENDERS = [
    ("men", _("Erkaklar")),
    ("women", _("Ayollar")),
    ("unique", "Unique"),      # erkak va ayolga birdek mos — hamma tilda «Unique»
    ("kids", _("Bolalar")),
    ("home", _("Uy va ofis")),
]

MECHANISMS = [
    ("automatic", _("Avtomatik")),
    ("mechanical", _("Mexanik (qo‘lda buraladi)")),
    ("quartz", _("Kvarts")),
    ("solar", _("Solar (quyosh quvvati)")),
    ("kinetic", _("Kinetik")),
    ("digital", _("Elektron (raqamli)")),
    ("smart", _("Smart")),
]

CASE_MATERIALS = [
    ("steel", _("Zanglamas po‘lat")),
    ("titanium", _("Titan")),
    ("gold", _("Oltin qoplama")),
    ("ceramic", _("Keramika")),
    ("bronze", _("Bronza")),
    ("aluminium", _("Alyuminiy")),
    ("resin", _("Plastik (rezina)")),
    ("wood", _("Yog‘och")),
    ("carbon", _("Karbon")),
]

STRAPS = [
    ("leather", _("Charm")),
    ("bracelet", _("Metall braslet")),
    ("mesh", _("Milan to‘ri")),
    ("rubber", _("Kauchuk")),
    ("silicone", _("Silikon")),
    ("nylon", _("Neylon (NATO)")),
    ("ceramic", _("Keramika")),
    ("chain", _("Zanjir")),
    ("none", _("Tasmasiz")),
]

GLASS = [
    ("sapphire", _("Safir")),
    ("mineral", _("Mineral")),
    ("acrylic", _("Akril")),
    ("glass", _("Oddiy oyna")),
]

# (kalit, nomi, rang) — rang filtrdagi doirachada va rasmda ishlatiladi
DIAL_COLORS = [
    ("black", _("Qora"), "#161616"),
    ("white", _("Oq"), "#f7f5f0"),
    ("silver", _("Kumushrang"), "#d5d8dc"),
    ("blue", _("Ko‘k"), "#1e3a68"),
    ("green", _("Yashil"), "#23493a"),
    ("grey", _("Kulrang"), "#5c6166"),
    ("champagne", _("Shampan"), "#e3cd9d"),
    ("brown", _("Jigarrang"), "#5b3c26"),
    ("red", _("Qizil"), "#8f2b25"),
    ("pink", _("Pushti"), "#ecc8c4"),
    ("cream", _("Krem"), "#efe3c8"),
]
DIAL_HEX = {key: hex_ for key, _label, hex_ in DIAL_COLORS}

CASE_SHAPES = [
    ("round", "Dumaloq"),
    ("square", "Kvadrat"),
    ("rect", "To‘g‘ri burchakli"),
    ("tonneau", "Bochka (tonneau)"),
    ("octagon", "Sakkiz qirrali"),
]

# Korpus rangi (rasm uchun)
CASE_FINISHES = [
    ("steel", "Kumushrang po‘lat"),
    ("gold", "Oltinrang"),
    ("rose", "Rose gold"),
    ("black", "Qora"),
    ("bronze", "Bronza"),
    ("titanium", "Kulrang titan"),
    ("white", "Oq"),
    ("wood", "Yog‘och"),
]

STRAP_COLORS = [
    ("metal", "Korpus rangida (metall)"),
    ("black", _("Qora")),
    ("brown", _("Jigarrang")),
    ("tan", _("Och jigarrang")),
    ("navy", _("To‘q ko‘k")),
    ("olive", _("Zaytun")),
    ("grey", _("Kulrang")),
    ("white", _("Oq")),
    ("pink", _("Pushti")),
    ("red", _("Qizil")),
    ("orange", _("To‘q sariq")),
    ("mint", _("Yalpiz")),
    ("yellow", _("Sariq")),
    ("sky", _("Havorang")),
]
STRAP_HEX = {
    "black": "#1d1c1b", "brown": "#6b4226", "tan": "#b07a45", "navy": "#1f2d4a",
    "olive": "#535c37", "grey": "#7b7f84", "white": "#f1efe9", "pink": "#e6b3b1",
    "red": "#b3332b", "orange": "#d9772b", "mint": "#97cfba", "yellow": "#efc24a",
    "sky": "#86b6dd",
}

BEZEL_COLORS = [
    ("", "Oddiy (korpus rangida)"),
    ("black", "Qora"),
    ("blue", "Ko‘k"),
    ("green", "Yashil"),
    ("red", "Qizil"),
    ("pepsi", "Qizil-ko‘k"),
    ("batman", "Ko‘k-qora"),
]

ART_STYLES = [
    ("classic", "Klassik"),
    ("sport", "Sport"),
    ("diver", "G‘avvos"),
    ("pilot", "Uchuvchi"),
    ("chrono", "Xronograf"),
    ("luxury", "Hashamatli"),
    ("field", "Harbiy"),
    ("digital", "Raqamli"),
    ("smart", "Smart"),
    ("kids", "Bolalar"),
    ("pocket", "Cho‘ntak"),
    ("wall", "Devor"),
    ("table", "Stol"),
    ("alarm", "Budilnik"),
]

# — Tasmalar (alohida mahsulot) —
STRAP_MATERIALS = [
    ("leather", _("Charm")),
    ("bracelet", _("Metall braslet")),
    ("mesh", _("Milan to‘ri")),
    ("rubber", _("Kauchuk")),
    ("silicone", _("Silikon")),
    ("nylon", _("Neylon (NATO)")),
]
STRAP_WIDTHS = [12, 14, 16, 18, 19, 20, 21, 22, 24]
# Qaysi soatga taqiladi: oddiy shpilkali soatlar kenglik bo‘yicha, Apple Watch — o‘z ulagichi bilan
STRAP_FITS = [
    ("pins", _("Oddiy shpilka")),
    ("quick", _("Tez yechiladigan shpilka")),
    ("apple_s", "Apple Watch 38–42 mm"),
    ("apple_l", "Apple Watch 44–49 mm"),
]
BUCKLES = [
    ("pin", _("Klassik to‘qa")),
    ("deployant", _("Kapalak qulf")),
    ("fold", _("Bukiladigan qulf")),
    ("magnet", _("Magnitli")),
    ("loop", _("Halqa (to‘qasiz)")),
]
# Tasma rangi: (kalit, nomi, filtrdagi doiracha rangi)
STRAP_PRODUCT_COLORS = [("metal", _("Metall"), "#b9bdc2")] + [
    (key, label, STRAP_HEX[key]) for key, label in STRAP_COLORS if key != "metal"]

REGIONS = [
    ("tashkent_city", _("Toshkent shahri")),
    ("tashkent", _("Toshkent viloyati")),
    ("andijan", _("Andijon viloyati")),
    ("bukhara", _("Buxoro viloyati")),
    ("fergana", _("Farg‘ona viloyati")),
    ("jizzakh", _("Jizzax viloyati")),
    ("khorezm", _("Xorazm viloyati")),
    ("namangan", _("Namangan viloyati")),
    ("navoi", _("Navoiy viloyati")),
    ("kashkadarya", _("Qashqadaryo viloyati")),
    ("karakalpakstan", _("Qoraqalpog‘iston Respublikasi")),
    ("samarkand", _("Samarqand viloyati")),
    ("syrdarya", _("Sirdaryo viloyati")),
    ("surkhandarya", _("Surxondaryo viloyati")),
]


def delivery_days(region):
    """Yetkazib berish muddati. Narxi hamma joyda 0 so‘m."""
    if region == "tashkent_city":
        return gettext("1 kun ichida")
    if region in ("tashkent", "syrdarya", "jizzakh"):
        return gettext("1–2 kun")
    if region in ("karakalpakstan", "khorezm", "surkhandarya"):
        return gettext("3–4 kun")
    return gettext("2–3 kun")
