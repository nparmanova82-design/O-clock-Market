"""Katalog filtrlari: soatlar uchun va tasmalar uchun alohida.

GET parametrlarini o‘qiydi, so‘rovga qo‘llaydi va har bir variant yonidagi sonni hisoblaydi.
Bir guruh ichidagi variantlar «yoki» bilan birlashadi (Seiko yoki Casio), guruhlar o‘zaro «va» bilan.
Funksiyalar bundan mustasno: tanlangan funksiyalarning hammasi bo‘lgan soatlar chiqadi.
Variant soni — shu variant ham tanlansa nechta mahsulot chiqishini ko‘rsatadi.
"""
from dataclasses import dataclass, field

from django.db.models import Case, Count, F, IntegerField, Max, Min, Q, Value, When
from django.utils.translation import gettext, gettext_lazy as _

from . import choices as ch
from .models import Brand, Category, Feature

SIZE_BUCKETS = [
    ("s", _("36 mm gacha"), 0, 36),
    ("m", "37–41 mm", 37, 41),
    ("l", "42–45 mm", 42, 45),
    ("xl", "46–60 mm", 46, 60),
]
WATER_OPTIONS = [("30", _("30 m dan")), ("50", _("50 m dan")), ("100", _("100 m dan")), ("200", _("200 m dan"))]
FLAGS = [
    ("aksiya", _("Faqat aksiyadagilar"), Q(old_price__gt=F("price"))),
    ("yangi", _("Yangi kelganlar"), Q(is_new=True)),
    ("mavjud", _("Faqat sotuvda borlari"), Q(stock__gt=0)),
]
SORTS = [
    ("ommabop", _("Ommabop")),
    ("yangi", _("Yangilari")),
    ("arzon", _("Avval arzonlari")),
    ("qimmat", _("Avval qimmatlari")),
    ("chegirma", _("Chegirmasi kattalari")),
]


@dataclass
class Facet:
    key: str
    label: str
    lookup: str
    options: list            # [(qiymat, nomi, rang yoki None)]
    kind: str = "check"      # check | color | bucket | all
    selected: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    locked: bool = False

    @property
    def items(self):
        for value, label, color in self.options:
            yield {"value": value, "label": label, "color": color,
                   "count": self.counts.get(value, 0), "checked": value in self.selected}


def _plain(choices):
    return [(k, v, None) for k, v in choices]


def _thousands(n):
    return f"{n:,}".replace(",", " ")


class BaseFilter:
    search_fields = ("name", "brand__name", "sku")
    has_water = False

    def __init__(self, params, base_qs, locked=None):
        self.params = params
        self.locked = locked or {}
        self.base = base_qs
        self.facets = self.build_facets()
        for f in self.facets:
            valid = {o[0] for o in f.options}
            if f.key in self.locked:
                f.selected, f.locked = list(self.locked[f.key]), True
            else:
                f.selected = [v for v in dict.fromkeys(params.getlist(f.key)) if v in valid]

        self.water = params.get("suv") if self.has_water and params.get("suv") in dict(WATER_OPTIONS) else ""
        self.flags = {k: (k in self.locked or params.get(k) == "1") for k, _l, _q in FLAGS}
        self.price_min = self._int(params.get("narx_min"))
        self.price_max = self._int(params.get("narx_max"))
        self.query = (params.get("q") or "").strip()[:80]
        self.sort_key = params.get("tartib") if params.get("tartib") in dict(SORTS) else "ommabop"
        self.water_counts, self.flag_counts, self.price_bounds = {}, {}, (0, 0)

    def build_facets(self):
        raise NotImplementedError

    @staticmethod
    def _int(value):
        try:
            v = int(str(value).replace(" ", ""))
        except (TypeError, ValueError):
            return None
        return v if v >= 0 else None

    # — qo‘llash —
    def apply(self, qs, skip=None):
        model = qs.model
        for f in self.facets:
            if f.key == skip or not f.selected:
                continue
            if f.kind == "bucket":
                q = Q()
                for key, _l, lo, hi in SIZE_BUCKETS:
                    if key in f.selected:
                        q |= Q(case_size__gte=lo, case_size__lte=hi)
                qs = qs.filter(q)
            elif f.kind == "all":
                for value in f.selected:
                    qs = qs.filter(pk__in=model.objects.filter(**{f.lookup: value}).values("pk"))
            else:
                qs = qs.filter(**{f"{f.lookup}__in": f.selected})
        if skip != "suv" and self.water:
            qs = qs.filter(water_resistance__gte=int(self.water))
        if skip != "narx":
            if self.price_min is not None:
                qs = qs.filter(price__gte=self.price_min)
            if self.price_max:
                qs = qs.filter(price__lte=self.price_max)
        for key, _l, q in FLAGS:
            if key != skip and self.flags[key]:
                qs = qs.filter(q)
        if self.query:
            for term in self.query.split():
                cond = Q()
                for name in self.search_fields:
                    cond |= Q(**{f"{name}__icontains": term})
                qs = qs.filter(cond)
        return qs

    def sort(self, qs):
        key = self.sort_key
        if key == "yangi":
            return qs.order_by("-created_at", "pk")
        if key == "arzon":
            return qs.order_by("price", "pk")
        if key == "qimmat":
            return qs.order_by("-price", "pk")
        if key == "chegirma":
            disc = Case(When(old_price__gt=F("price"), then=(F("old_price") - F("price")) * 100 / F("old_price")),
                        default=Value(0), output_field=IntegerField())
            return qs.annotate(disc=disc).order_by("-disc", "price", "pk")
        return qs.order_by("-is_hit", "-sold", "-created_at", "pk")

    def results(self):
        return self.sort(self.apply(self.base))

    # — variantlar soni —
    def compute_counts(self):
        for f in self.facets:
            if f.locked:
                continue
            qs = self.apply(self.base) if f.kind == "all" else self.apply(self.base, skip=f.key)
            if f.kind == "bucket":
                f.counts = qs.aggregate(**{key: Count("pk", filter=Q(case_size__gte=lo, case_size__lte=hi))
                                           for key, _l, lo, hi in SIZE_BUCKETS})
            else:
                rows = qs.order_by().values(f.lookup).annotate(c=Count("pk", distinct=True))
                f.counts = {str(r[f.lookup]): r["c"] for r in rows}
        if self.has_water:
            qs = self.apply(self.base, skip="suv")
            self.water_counts = qs.aggregate(**{f"w{v}": Count("pk", filter=Q(water_resistance__gte=int(v)))
                                                for v, _l in WATER_OPTIONS})
        self.flag_counts = {key: self.apply(self.base, skip=key).filter(q).count() for key, _l, q in FLAGS}
        bounds = self.base.aggregate(lo=Min("price"), hi=Max("price"))
        self.price_bounds = (bounds["lo"] or 0, bounds["hi"] or 0)

    # — shablon uchun —
    @property
    def visible_facets(self):
        return [f for f in self.facets if not f.locked and f.options]

    def water_items(self):
        if not self.has_water:
            return []
        return [{"value": v, "label": lab, "checked": v == self.water,
                 "count": self.water_counts.get(f"w{v}", 0)} for v, lab in WATER_OPTIONS]

    def flag_items(self):
        return [{"key": k, "label": lab, "checked": self.flags[k], "count": self.flag_counts.get(k, 0)}
                for k, lab, _q in FLAGS if k not in self.locked]

    def _url(self, drop_key=None, drop_value=None):
        params = self.params.copy()
        params.pop("sahifa", None)
        if drop_key:
            if drop_value is None:
                params.pop(drop_key, None)
            else:
                params.setlist(drop_key, [v for v in params.getlist(drop_key) if v != drop_value])
        encoded = params.urlencode()
        return f"?{encoded}" if encoded else "?"

    def chips(self):
        chips = []
        if self.query:
            chips.append((f"«{self.query}»", self._url("q")))
        for f in self.facets:
            if f.locked:
                continue
            labels = {o[0]: o[1] for o in f.options}
            for value in f.selected:
                chips.append((labels[value], self._url(f.key, value)))
        if self.water:
            chips.append((gettext("Suvga chidamli: %(v)s") % {"v": dict(WATER_OPTIONS)[self.water]},
                          self._url("suv")))
        if self.price_min is not None or self.price_max:
            lo = _thousands(self.price_min) if self.price_min is not None else "0"
            hi = _thousands(self.price_max) if self.price_max else "…"
            params = self.params.copy()
            for k in ("narx_min", "narx_max", "sahifa"):
                params.pop(k, None)
            chips.append((gettext("Narx: %(lo)s – %(hi)s") % {"lo": lo, "hi": hi}, f"?{params.urlencode()}"))
        for key, label, _q in FLAGS:
            if self.flags[key] and key not in self.locked:
                chips.append((label, self._url(key)))
        return chips

    @property
    def active_count(self):
        return len(self.chips())


class CatalogFilter(BaseFilter):
    """Soatlar katalogi."""
    search_fields = ("name", "brand__name", "sku", "category__name", "category__name_ru", "category__name_en")
    has_water = True

    def build_facets(self):
        return [
            Facet("turi", _("Soat turi"), "category__slug",
                  [(c.slug, c.local_name, None) for c in Category.objects.all()]),
            Facet("kimga", _("Kimga"), "gender", _plain(ch.GENDERS)),
            Facet("brend", _("Brend"), "brand__slug",
                  [(b.slug, b.name, None) for b in Brand.objects.filter(watches__isnull=False).distinct()]),
            Facet("mexanizm", _("Mexanizm"), "mechanism", _plain(ch.MECHANISMS)),
            Facet("olcham", _("Korpus diametri"), "case_size", [(k, lab, None) for k, lab, _lo, _hi in SIZE_BUCKETS],
                  kind="bucket"),
            Facet("rang", _("Siferblat rangi"), "dial_color", ch.DIAL_COLORS, kind="color"),
            Facet("korpus", _("Korpus materiali"), "case_material", _plain(ch.CASE_MATERIALS)),
            Facet("tasma", _("Tasma materiali"), "strap_material", _plain(ch.STRAPS)),
            Facet("oyna", _("Oyna"), "glass", _plain(ch.GLASS)),
            Facet("funksiya", _("Funksiyalar"), "features__slug",
                  [(f.slug, f.local_name, None) for f in Feature.objects.all()], kind="all"),
        ]


class StrapFilter(BaseFilter):
    """Tasmalar bo‘limining alohida «Tasma» filtri."""
    search_fields = ("name", "name_ru", "name_en", "brand__name", "sku")

    def build_facets(self):
        return [
            Facet("kenglik", _("Kengligi"), "width", [(str(w), f"{w} mm", None) for w in ch.STRAP_WIDTHS]),
            Facet("moslik", _("Ulanishi"), "fit", _plain(ch.STRAP_FITS)),
            Facet("material", _("Material"), "material", _plain(ch.STRAP_MATERIALS)),
            Facet("rang", _("Rangi"), "color", ch.STRAP_PRODUCT_COLORS, kind="color"),
            Facet("qulf", _("Qulf"), "buckle", _plain(ch.BUCKLES)),
            Facet("brend", _("Brend"), "brand__slug",
                  [(b.slug, b.name, None) for b in Brand.objects.filter(straps__isnull=False).distinct()]),
        ]
