"""O’clock market katalogi: brendlar, soat turlari, funksiyalar, soatlar va tasmalar.

Matnli maydonlarning ruscha va inglizcha nusxasi bor (name_ru, name_en ...). Saytda joriy tilga mos
nusxa ko‘rsatiladi, u bo‘sh bo‘lsa — o‘zbekchasi (`local_*` xossalari).
"""
from django.db import models
from django.urls import reverse
from django.utils.translation import get_language

from . import choices as ch

LANG_SUFFIXES = ("ru", "en")


class Localized:
    def local(self, field):
        lang = (get_language() or "uz")[:2]
        if lang in LANG_SUFFIXES:
            value = getattr(self, f"{field}_{lang}", "")
            if value:
                return value
        return getattr(self, field)


def _ru(label, field=models.CharField, **kw):
    return field(f"{label} (ruscha)", blank=True, **kw)


def _en(label, field=models.CharField, **kw):
    return field(f"{label} (inglizcha)", blank=True, **kw)


class Brand(Localized, models.Model):
    name = models.CharField("Nomi", max_length=80, unique=True)
    slug = models.SlugField("Slug", unique=True)
    country = models.CharField("Davlati", max_length=60, blank=True)
    country_ru = _ru("Davlati", max_length=60)
    country_en = _en("Davlati", max_length=60)
    description = models.TextField("Tavsif", blank=True)
    description_ru = _ru("Tavsif", models.TextField)
    description_en = _en("Tavsif", models.TextField)

    class Meta:
        ordering = ["name"]
        verbose_name = "brend"
        verbose_name_plural = "brendlar"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("shop:brand", args=[self.slug])

    @property
    def local_country(self):
        return self.local("country")

    @property
    def local_description(self):
        return self.local("description")


class Category(Localized, models.Model):
    """Soat turi: klassik, g‘avvos, smart, devor soati va h.k."""
    name = models.CharField("Nomi", max_length=80)
    name_ru = _ru("Nomi", max_length=80)
    name_en = _en("Nomi", max_length=80)
    slug = models.SlugField("Slug", unique=True)
    short = models.CharField("Qisqa tavsif", max_length=200, blank=True)
    short_ru = _ru("Qisqa tavsif", max_length=200)
    short_en = _en("Qisqa tavsif", max_length=200)
    art_style = models.CharField("Rasm uslubi", max_length=20, choices=ch.ART_STYLES, default="classic")
    order = models.PositiveSmallIntegerField("Tartib", default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "soat turi"
        verbose_name_plural = "soat turlari"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("shop:catalog") + f"?turi={self.slug}"

    @property
    def local_name(self):
        return self.local("name")

    @property
    def local_short(self):
        return self.local("short")


class Feature(Localized, models.Model):
    name = models.CharField("Nomi", max_length=60)
    name_ru = _ru("Nomi", max_length=60)
    name_en = _en("Nomi", max_length=60)
    slug = models.SlugField("Slug", unique=True)
    order = models.PositiveSmallIntegerField("Tartib", default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "funksiya"
        verbose_name_plural = "funksiyalar"

    def __str__(self):
        return self.name

    @property
    def local_name(self):
        return self.local("name")


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def on_sale(self):
        return self.filter(old_price__gt=models.F("price"))


WatchQuerySet = ProductQuerySet


class Product:
    """Soat va tasma uchun umumiy: narx, chegirma va ombor."""
    kind = ""

    @property
    def is_sale(self):
        return bool(self.old_price and self.old_price > self.price)

    @property
    def discount_percent(self):
        if not self.is_sale:
            return 0
        return round((self.old_price - self.price) * 100 / self.old_price)

    @property
    def saving(self):
        return self.old_price - self.price if self.is_sale else 0

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def title(self):
        return str(self)

    @property
    def cart_key(self):
        return f"{self.kind[0]}{self.pk}"


class Watch(Product, Localized, models.Model):
    kind = "watch"

    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="watches", verbose_name="Brend")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="watches",
                                 verbose_name="Soat turi")
    name = models.CharField("Nomi", max_length=140)
    slug = models.SlugField("Slug", max_length=160, unique=True)
    sku = models.CharField("Artikul", max_length=40, blank=True)
    gender = models.CharField("Kimga", max_length=10, choices=ch.GENDERS, default="unique",
                              help_text="Unique — erkak va ayolga birdek mos soat")
    mechanism = models.CharField("Mexanizm", max_length=12, choices=ch.MECHANISMS, default="quartz")
    case_material = models.CharField("Korpus materiali", max_length=12, choices=ch.CASE_MATERIALS,
                                     default="steel")
    strap_material = models.CharField("Tasma", max_length=12, choices=ch.STRAPS, default="leather")
    lug_width = models.PositiveSmallIntegerField(
        "Tasma kengligi (mm)", null=True, blank=True,
        help_text="Mos tasmalarni ko‘rsatish uchun. Integratsiyalashgan braslet, Apple Watch, devor va stol "
                  "soatlarida bo‘sh qoldiring")
    glass = models.CharField("Oyna", max_length=10, choices=ch.GLASS, default="mineral")
    case_size = models.PositiveSmallIntegerField("Korpus diametri (mm)", default=40,
                                                 help_text="Devor/stol soatlarida — siferblat diametri")
    thickness = models.DecimalField("Qalinligi (mm)", max_digits=4, decimal_places=1, null=True, blank=True)
    water_resistance = models.PositiveSmallIntegerField("Suvga chidamlilik (m)", default=30)
    features = models.ManyToManyField(Feature, blank=True, related_name="watches", verbose_name="Funksiyalar")

    price = models.PositiveIntegerField("Narxi (so‘m)")
    old_price = models.PositiveIntegerField("Eski narxi (so‘m)", null=True, blank=True,
                                            help_text="Aksiya uchun: narxdan katta bo‘lsa, chegirma ko‘rsatiladi")
    stock = models.PositiveIntegerField("Omborda (dona)", default=10)
    warranty_months = models.PositiveSmallIntegerField("Kafolat (oy)", default=12)
    is_new = models.BooleanField("Yangi", default=False)
    is_hit = models.BooleanField("Xit", default=False)
    is_active = models.BooleanField("Saytda ko‘rinadi", default=True)
    sold = models.PositiveIntegerField("Sotilgan", default=0, editable=False)

    description = models.TextField("Tavsif", blank=True)
    description_ru = _ru("Tavsif", models.TextField)
    description_en = _en("Tavsif", models.TextField)
    image = models.ImageField("Surat", upload_to="watches/", blank=True,
                              help_text="Yuklanmasa, sayt soat rasmini o‘zi chizadi")

    # — Chiziladigan rasm sozlamalari —
    art_style = models.CharField("Rasm uslubi", max_length=20, choices=ch.ART_STYLES, blank=True,
                                 help_text="Bo‘sh bo‘lsa, soat turidagi uslub olinadi")
    case_shape = models.CharField("Korpus shakli", max_length=10, choices=ch.CASE_SHAPES, default="round")
    case_finish = models.CharField("Korpus rangi", max_length=10, choices=ch.CASE_FINISHES, default="steel")
    dial_color = models.CharField("Siferblat rangi", max_length=10, choices=[c[:2] for c in ch.DIAL_COLORS],
                                  default="black")
    strap_color = models.CharField("Tasma rangi", max_length=10, choices=ch.STRAP_COLORS, default="black",
                                   help_text="Devor, stol soati va budilnikda — korpus rangi")
    bezel_color = models.CharField("Bezel rangi", max_length=10, choices=ch.BEZEL_COLORS, blank=True)

    created_at = models.DateTimeField("Qo‘shilgan", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan", auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "soat"
        verbose_name_plural = "soatlar"
        indexes = [models.Index(fields=["is_active", "price"])]

    def __str__(self):
        return f"{self.brand.name} {self.name}"

    def get_absolute_url(self):
        return reverse("shop:watch", args=[self.slug])

    @property
    def style(self):
        return self.art_style or self.category.art_style

    @property
    def is_unique(self):
        return self.gender == "unique"

    @property
    def local_description(self):
        return self.local("description")

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        from .watch_art import ART_VERSION

        return reverse("art:watch_svg", args=[self.slug]) + f"?v={int(self.updated_at.timestamp())}-{ART_VERSION}"

    @property
    def dial_hex(self):
        return ch.DIAL_HEX.get(self.dial_color, "#161616")

    @property
    def strap_fit(self):
        """Qaysi tasmalar mos keladi: Apple Watch — o‘z ulagichi, boshqalar — kenglik bo‘yicha."""
        if self.brand.slug == "apple" and self.mechanism == "smart":
            return "apple_s" if self.case_size <= 42 else "apple_l"
        return "width" if self.lug_width else ""

    def short_specs(self):
        """Kartochkadagi qisqa satr: «Avtomatik · 40 mm · 100 m»."""
        parts = [str(self.get_mechanism_display()).split(" (")[0], f"{self.case_size} mm"]
        if self.water_resistance:
            parts.append(f"{self.water_resistance} m")
        return " · ".join(parts)


class Strap(Product, Localized, models.Model):
    """Qo‘l soati uchun alohida sotiladigan tasma."""
    kind = "strap"

    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="straps", verbose_name="Brend")
    name = models.CharField("Nomi", max_length=140)
    name_ru = _ru("Nomi", max_length=140)
    name_en = _en("Nomi", max_length=140)
    slug = models.SlugField("Slug", max_length=160, unique=True)
    sku = models.CharField("Artikul", max_length=40, blank=True)
    material = models.CharField("Material", max_length=12, choices=ch.STRAP_MATERIALS, default="leather")
    color = models.CharField("Rangi", max_length=10, choices=[c[:2] for c in ch.STRAP_PRODUCT_COLORS],
                             default="black")
    finish = models.CharField("Metall qismlar rangi", max_length=10, choices=ch.CASE_FINISHES, default="steel",
                              help_text="To‘qa va qulf rangi; metall braslet va Milan to‘rida — tasmaning o‘zi")
    width = models.PositiveSmallIntegerField(
        "Kengligi (mm)", null=True, blank=True, choices=[(w, f"{w} mm") for w in ch.STRAP_WIDTHS],
        help_text="Apple Watch tasmalarida bo‘sh qoldiring")
    fit = models.CharField("Ulanishi", max_length=10, choices=ch.STRAP_FITS, default="pins")
    buckle = models.CharField("Qulf", max_length=10, choices=ch.BUCKLES, default="pin")

    price = models.PositiveIntegerField("Narxi (so‘m)")
    old_price = models.PositiveIntegerField("Eski narxi (so‘m)", null=True, blank=True)
    stock = models.PositiveIntegerField("Omborda (dona)", default=20)
    is_new = models.BooleanField("Yangi", default=False)
    is_hit = models.BooleanField("Xit", default=False)
    is_active = models.BooleanField("Saytda ko‘rinadi", default=True)
    sold = models.PositiveIntegerField("Sotilgan", default=0, editable=False)

    description = models.TextField("Tavsif", blank=True)
    description_ru = _ru("Tavsif", models.TextField)
    description_en = _en("Tavsif", models.TextField)
    image = models.ImageField("Surat", upload_to="straps/", blank=True,
                              help_text="Yuklanmasa, sayt tasma rasmini o‘zi chizadi")

    created_at = models.DateTimeField("Qo‘shilgan", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan", auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "tasma"
        verbose_name_plural = "tasmalar"

    def __str__(self):
        return f"{self.brand.name} {self.local_name}"

    def get_absolute_url(self):
        return reverse("shop:strap", args=[self.slug])

    @property
    def local_name(self):
        return self.local("name")

    @property
    def local_description(self):
        return self.local("description")

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        from .watch_art import ART_VERSION

        return reverse("art:strap_svg", args=[self.slug]) + f"?v={int(self.updated_at.timestamp())}-{ART_VERSION}"

    @property
    def is_apple(self):
        return self.fit.startswith("apple")

    def fit_label(self):
        """«20 mm, tez yechiladigan shpilka» yoki «Apple Watch 44–49 mm»."""
        if self.is_apple:
            return str(self.get_fit_display())
        return f"{self.width} mm, {str(self.get_fit_display()).lower()}" if self.width else str(self.get_fit_display())

    def short_specs(self):
        """Kartochkadagi qisqa satr: «Charm · Klassik to‘qa» (kenglik alohida belgida ko‘rsatiladi)."""
        return " · ".join([str(self.get_material_display()).split(" (")[0], str(self.get_buckle_display())])
