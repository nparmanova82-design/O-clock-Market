import random

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from shop.choices import REGIONS, delivery_days


class PromoCode(models.Model):
    code = models.CharField("Kod", max_length=30, unique=True, help_text="Katta harflarda, masalan AEVUM10")
    percent = models.PositiveSmallIntegerField("Chegirma (%)")
    min_total = models.PositiveIntegerField("Minimal summa (so‘m)", default=0)
    is_active = models.BooleanField("Faol", default=True)
    valid_until = models.DateField("Amal qilish muddati", null=True, blank=True)

    class Meta:
        verbose_name = "promokod"
        verbose_name_plural = "promokodlar"

    def __str__(self):
        return f"{self.code} (−{self.percent}%)"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return self.is_active and (not self.valid_until or self.valid_until >= timezone.localdate())


class Order(models.Model):
    STATUSES = [
        ("new", _("Yangi")),
        ("confirmed", _("Tasdiqlandi")),
        ("shipping", _("Yo‘lda")),
        ("delivered", _("Yetkazildi")),
        ("cancelled", _("Bekor qilindi")),
    ]
    PAYMENTS = [
        ("cash", _("Naqd pul")),
        ("card", _("Karta orqali")),
    ]

    number = models.CharField("Raqami", max_length=20, unique=True, editable=False)
    full_name = models.CharField(_("Ism familiya"), max_length=120)
    phone = models.CharField(_("Telefon"), max_length=20)
    region = models.CharField(_("Viloyat"), max_length=20, choices=REGIONS)
    city = models.CharField(_("Shahar / tuman"), max_length=80)
    address = models.CharField(_("Manzil"), max_length=255)
    comment = models.TextField(_("Izoh"), blank=True)
    payment = models.CharField(_("To‘lov usuli"), max_length=10, choices=PAYMENTS, default="cash")
    gift_wrap = models.BooleanField(_("Sovg‘a qutisi"), default=False)
    promo_code = models.CharField("Promokod", max_length=30, blank=True)

    subtotal = models.PositiveIntegerField("Mahsulotlar", default=0)
    discount = models.PositiveIntegerField("Promokod chegirmasi", default=0)
    delivery_cost = models.PositiveIntegerField("Yetkazib berish", default=0)
    total = models.PositiveIntegerField("Jami", default=0)

    status = models.CharField("Holati", max_length=12, choices=STATUSES, default="new")
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "buyurtma"
        verbose_name_plural = "buyurtmalar"

    def __str__(self):
        return f"№ {self.number}"

    def save(self, *args, **kwargs):
        if not self.number:
            prefix = timezone.localtime().strftime("%y%m%d")
            while True:
                number = f"OC-{prefix}-{random.randint(1000, 9999)}"
                if not Order.objects.filter(number=number).exists():
                    self.number = number
                    break
        super().save(*args, **kwargs)

    @property
    def delivery_days(self):
        return delivery_days(self.region)

    @property
    def items_count(self):
        return sum(i.quantity for i in self.items.all())

    @property
    def status_step(self):
        order = ["new", "confirmed", "shipping", "delivered"]
        return order.index(self.status) if self.status in order else -1


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    watch = models.ForeignKey("shop.Watch", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
                              verbose_name="Soat")
    strap = models.ForeignKey("shop.Strap", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
                              verbose_name="Tasma")
    title = models.CharField("Nomi", max_length=200)
    price = models.PositiveIntegerField("Narxi")
    quantity = models.PositiveIntegerField("Soni", default=1)

    class Meta:
        verbose_name = "mahsulot"
        verbose_name_plural = "mahsulotlar"

    def __str__(self):
        return self.title

    @property
    def total(self):
        return self.price * self.quantity

    @property
    def product(self):
        return self.watch or self.strap


class Callback(models.Model):
    name = models.CharField(_("Ism"), max_length=80)
    phone = models.CharField("Telefon", max_length=20)
    message = models.TextField(_("Savolingiz"), blank=True)
    is_done = models.BooleanField("Javob berildi", default=False)
    created_at = models.DateTimeField("Yuborilgan", auto_now_add=True)

    class Meta:
        ordering = ["is_done", "-created_at"]
        verbose_name = "qayta qo‘ng‘iroq so‘rovi"
        verbose_name_plural = "qayta qo‘ng‘iroq so‘rovlari"

    def __str__(self):
        return f"{self.name} — {self.phone}"
