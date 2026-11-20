"""Sessiyadagi savatcha va buyurtma summasi.

Savatcha sessiyada {kalit: soni} ko‘rinishida turadi: «w12» — 12-soat, «s5» — 5-tasma
(eski savatchalardagi faqat raqamli kalitlar soat deb o‘qiladi). Narxlar har safar bazadan olinadi,
shuning uchun admin narxni o‘zgartirsa, savatchada ham darhol yangilanadi.
Yetkazib berish O‘zbekiston bo‘ylab bepul — summaga hech qachon qo‘shilmaydi.
"""
import re

from django.utils.translation import gettext as _

CART_KEY = "cart"
PROMO_KEY = "promo_code"
KEY_RE = re.compile(r"^([ws])(\d+)$")


def normalize_key(key):
    key = str(key)
    if key.isdigit():
        key = "w" + key
    return key if KEY_RE.match(key) else None


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.data = {}
        for k, v in self.session.get(CART_KEY, {}).items():
            key = normalize_key(k)
            try:
                if key:
                    self.data[key] = max(0, int(v))
            except (TypeError, ValueError):
                continue
        self._lines = None

    def _save(self):
        self.session[CART_KEY] = self.data
        self._lines = None

    def __len__(self):
        return sum(self.data.values())

    def quantity_of(self, item):
        return self.data.get(item.cart_key, 0)

    def add(self, item, quantity=1, replace=False):
        """Soat yoki tasma qo‘shadi. Soni ombordagi qoldiqdan oshmaydi. Savatchadagi yangi sonni qaytaradi."""
        key = item.cart_key
        new_qty = quantity if replace else self.data.get(key, 0) + quantity
        new_qty = max(0, min(new_qty, item.stock))
        if new_qty:
            self.data[key] = new_qty
        else:
            self.data.pop(key, None)
        self._save()
        return new_qty

    def remove(self, key):
        self.data.pop(normalize_key(key) or "", None)
        self._save()

    def clear(self):
        self.data = {}
        self._save()
        self.session.pop(PROMO_KEY, None)

    def lines(self):
        if self._lines is None:
            from shop.models import Strap, Watch

            ids = {"w": [], "s": []}
            for key in self.data:
                kind, pk = KEY_RE.match(key).groups()
                ids[kind].append(int(pk))
            items = {}
            for w in Watch.objects.active().filter(pk__in=ids["w"]).select_related("brand", "category"):
                items[w.cart_key] = w
            for s in Strap.objects.active().filter(pk__in=ids["s"]).select_related("brand"):
                items[s.cart_key] = s
            self._lines = []
            for key, qty in self.data.items():
                item = items.get(key)
                if not item:
                    continue
                self._lines.append({
                    "key": key,
                    "item": item,
                    "quantity": qty,
                    "price": item.price,
                    "total": item.price * qty,
                    "saving": item.saving * qty,
                    "over_stock": qty > item.stock,
                })
        return self._lines

    @property
    def subtotal(self):
        return sum(line["total"] for line in self.lines())

    @property
    def sale_saving(self):
        return sum(line["saving"] for line in self.lines())

    # — promokod —
    def promo(self):
        from .models import PromoCode

        code = self.session.get(PROMO_KEY)
        if not code:
            return None
        promo = PromoCode.objects.filter(code=code).first()
        return promo if promo and promo.is_valid else None

    def set_promo(self, code):
        self.session[PROMO_KEY] = code

    def drop_promo(self):
        self.session.pop(PROMO_KEY, None)

    def quote(self):
        return quote(self.subtotal, self.promo())


def quote(subtotal, promo=None):
    from shop.utils import som

    discount = 0
    promo_note = ""
    if promo:
        if subtotal >= promo.min_total:
            discount = subtotal * promo.percent // 100
        else:
            promo_note = _("%(code)s kodi %(sum)s dan boshlab ishlaydi") % {"code": promo.code,
                                                                          "sum": som(promo.min_total)}
    return {
        "subtotal": subtotal,
        "discount": discount,
        "promo_note": promo_note,
        "delivery_cost": 0,
        "total": subtotal - discount,
    }
