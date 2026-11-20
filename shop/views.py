from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from orders.cart import Cart

from . import choices as ch
from . import seo
from .filters import SORTS, CatalogFilter, StrapFilter
from .models import Brand, Category, Strap, Watch
from .session_lists import Recent, Wishlist
from .utils import som
from .watch_art import default_spec, render as render_art, render_strap, render_watch

PER_PAGE = 24


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _cards(qs):
    return qs.select_related("brand", "category")


def _strap_cards(qs):
    return qs.select_related("brand")


def home(request):
    active = _cards(Watch.objects.active())
    hero = (active.filter(is_hit=True, category__art_style__in=["luxury", "diver", "sport", "classic"])
            .order_by("-price").first() or active.first())
    categories = Category.objects.annotate(n=Count("watches", filter=Q(watches__is_active=True)))
    return render(request, "shop/home.html", {
        "hero": hero,
        "hero_svg": mark_safe(render_watch(hero, uid="hero", live=True)) if hero else "",
        "categories": categories,
        "sale_watches": active.on_sale().order_by("-is_hit", "-old_price")[:8],
        "unique_watches": active.filter(gender="unique").order_by("-is_hit", "-created_at")[:3],
        "new_watches": active.filter(is_new=True)[:8],
        "hit_watches": active.filter(is_hit=True).order_by("-sold")[:4],
        "home_straps": _strap_cards(Strap.objects.active()).order_by("-is_hit", "-sold")[:4],
        "strap_widths": [16, 18, 20, 22, 24],
        "brands": Brand.objects.annotate(n=Count("watches", filter=Q(watches__is_active=True))).filter(n__gt=0),
        "regions": ch.REGIONS,
        "total_watches": active.count(),
        "jsonld": seo.script(request, seo.store(request), seo.website(request)),
    })


def _listing(request, *, title, lead="", locked=None, base, filter_class, kind, section, indexable=("sahifa",),
             crumbs=None, extra=None):
    """Katalog sahifasi: chap tomonda filtr, o‘ngda kartochkalar. Soatlar ham, tasmalar ham shu yerdan."""
    flt = filter_class(request.GET, base, locked=locked)
    flt.compute_counts()
    page = Paginator(flt.results(), PER_PAGE).get_page(request.GET.get("sahifa"))

    # Filtrlangan, saralangan va qidiruv sahifalari indekslanmaydi: ular asosiy sahifaning nusxasi.
    # Bitta soat turi (?turi=gavvos) esa o‘z sahifasi sifatida indekslanadi.
    params = request.GET
    single = {k: params.getlist(k) for k in indexable if k != "sahifa"}
    extra_params = [k for k in params if k not in indexable and any(params.getlist(k))]
    noindex = bool(extra_params) or any(len(v) > 1 for v in single.values())
    canonical = {k: v[0] for k, v in single.items() if len(v) == 1}
    if page.number > 1 and not noindex:
        canonical["sahifa"] = page.number
    canonical_url = request.build_absolute_uri(request.path)
    if canonical:
        canonical_url += "?" + urlencode(canonical)

    ctx = {
        "title": title,
        "lead": lead,
        "kind": kind,
        "section": section,
        "card_template": "includes/strap_card.html" if section == "straps" else "includes/watch_card.html",
        "filter": flt,
        "page": page,
        "sorts": SORTS,
        "chips": flt.chips(),
        "crumbs": crumbs or [],
        "noindex": noindex,
        "canonical_url": canonical_url,
        "jsonld": seo.script(request, seo.breadcrumbs(request, crumbs or [])),
    }
    ctx.update(extra or {})
    return render(request, "shop/catalog.html", ctx)


def _catalog(request, *, title, lead="", locked=None, kind="catalog", extra=None):
    turi = request.GET.getlist("turi")
    crumbs = [(_("Bosh sahifa"), reverse("shop:home")), (_("Katalog"), reverse("shop:catalog"))]
    if kind != "catalog" or len(turi) == 1:
        crumbs.append((title, None))
    return _listing(request, title=title, lead=lead, locked=locked, base=_cards(Watch.objects.active()),
                    filter_class=CatalogFilter, kind=kind, section="watches", indexable=("turi", "sahifa"),
                    crumbs=crumbs, extra=extra)


def catalog(request):
    title, lead = _("Katalog"), _("Barcha turdagi soatlar: qo‘l soatlaridan devor soatlarigacha.")
    slugs = request.GET.getlist("turi")
    if len(slugs) == 1:
        cat = Category.objects.filter(slug=slugs[0]).first()
        if cat:
            title, lead = cat.local_name, cat.local_short
    if request.GET.get("q"):
        title = _("Qidiruv: «%(q)s»") % {"q": request.GET["q"].strip()[:80]}
        lead = ""
    return _catalog(request, title=title, lead=lead)


def sale(request):
    return _catalog(request, title=_("Aksiya va chegirmalar"), kind="sale",
                    lead=_("Oy oxirigacha amal qiladigan narxlar. Chegirma narxga allaqachon qo‘shilgan."),
                    locked={"aksiya": ["1"]})


def unique(request):
    return _catalog(request, title="Unique", kind="unique",
                    lead=_("Erkak va ayolga birdek mos soatlar — neytral dizayn, o‘rtacha o‘lcham, "
                           "har qanday bilakka yarashadi."),
                    locked={"kimga": ["unique"]})


def new_arrivals(request):
    return _catalog(request, title=_("Yangi kelganlar"), kind="new",
                    lead=_("Do‘konimizga yaqinda kelgan modellar."), locked={"yangi": ["1"]})


def brands(request):
    items = Brand.objects.annotate(n=Count("watches", filter=Q(watches__is_active=True))).filter(n__gt=0)
    return render(request, "shop/brands.html", {"brands": items})


def brand_detail(request, slug):
    brand = get_object_or_404(Brand, slug=slug)
    lead = " · ".join(filter(None, [brand.local_country, brand.local_description]))
    return _catalog(request, title=brand.name, lead=lead, kind="brand", locked={"brend": [brand.slug]},
                    extra={"brand": brand})


def straps(request):
    title = _("Tasmalar")
    lead = _("Qo‘l soatlari uchun charm, silikon, neylon va metall tasmalar. Kenglik va ulanish turi bo‘yicha "
             "tanlang — yetkazib berish bepul.")
    if request.GET.get("q"):
        title = _("Qidiruv: «%(q)s»") % {"q": request.GET["q"].strip()[:80]}
    crumbs = [(_("Bosh sahifa"), reverse("shop:home")), (_("Tasmalar"), None)]
    return _listing(request, title=title, lead=lead, base=_strap_cards(Strap.objects.active()),
                    filter_class=StrapFilter, kind="straps", section="straps", crumbs=crumbs)


def matching_straps(watch, limit=4):
    """Soatga mos tasmalar va ularning hammasini ko‘rsatadigan havola."""
    fit = watch.strap_fit
    qs = _strap_cards(Strap.objects.active())
    if fit in ("apple_s", "apple_l"):
        qs, query = qs.filter(fit=fit), {"moslik": fit}
    elif fit == "width":
        qs, query = qs.filter(width=watch.lug_width).exclude(fit__startswith="apple"), {"kenglik": watch.lug_width}
    else:
        return [], ""
    return list(qs.order_by("-is_hit", "-sold")[:limit]), reverse("shop:straps") + "?" + urlencode(query)


def watch_detail(request, slug):
    watch = get_object_or_404(
        Watch.objects.active().select_related("brand", "category").prefetch_related("features"), slug=slug)
    recent = Recent(request)
    recent_ids = [i for i in recent.ids if i != watch.pk][:4]
    recent.push(watch.pk)
    by_id = {w.pk: w for w in _cards(Watch.objects.active().filter(pk__in=recent_ids))}

    specs = [
        (_("Brend"), watch.brand.name),
        (_("Soat turi"), watch.category.local_name),
        (_("Kimga"), _("Unique — erkak va ayolga mos") if watch.is_unique else watch.get_gender_display()),
        (_("Mexanizm"), watch.get_mechanism_display()),
        (_("Korpus diametri"), f"{watch.case_size} mm"),
        (_("Qalinligi"), f"{watch.thickness} mm" if watch.thickness else None),
        (_("Korpus materiali"), watch.get_case_material_display()),
        (_("Tasma"), watch.get_strap_material_display() if watch.strap_material != "none" else None),
        (_("Tasma kengligi"), f"{watch.lug_width} mm" if watch.lug_width else None),
        (_("Oyna"), watch.get_glass_display()),
        (_("Siferblat rangi"), watch.get_dial_color_display()),
        (_("Suvga chidamlilik"), f"{watch.water_resistance} m" if watch.water_resistance else _("Yo‘q")),
        (_("Funksiyalar"), ", ".join(f.local_name for f in watch.features.all()) or None),
        (_("Kafolat"), _("%(n)s oy") % {"n": watch.warranty_months}),
        (_("Artikul"), watch.sku or None),
    ]
    related = (_cards(Watch.objects.active()).filter(category=watch.category).exclude(pk=watch.pk)
               .order_by("-is_hit", "?")[:4])
    fitting, fitting_url = matching_straps(watch)
    return render(request, "shop/watch_detail.html", {
        "watch": watch,
        "specs": [(k, v) for k, v in specs if v],
        "related": related,
        "recent": [by_id[i] for i in recent_ids if i in by_id],
        "fitting_straps": fitting,
        "fitting_url": fitting_url,
        "in_cart": Cart(request).quantity_of(watch),
        "regions": ch.REGIONS,
        "region_days": {key: ch.delivery_days(key) for key, _label in ch.REGIONS},
        "jsonld": seo.script(request, seo.product(request, watch), seo.breadcrumbs(request, [
            (_("Bosh sahifa"), reverse("shop:home")), (_("Katalog"), reverse("shop:catalog")),
            (watch.category.local_name, watch.category.get_absolute_url()), (str(watch), None)])),
    })


def strap_detail(request, slug):
    strap = get_object_or_404(Strap.objects.active().select_related("brand"), slug=slug)
    specs = [
        (_("Brend"), strap.brand.name),
        (_("Material"), strap.get_material_display()),
        (_("Rangi"), strap.get_color_display()),
        (_("Kengligi"), f"{strap.width} mm" if strap.width else None),
        (_("Ulanishi"), strap.get_fit_display()),
        (_("Qulf"), strap.get_buckle_display()),
        (_("Artikul"), strap.sku or None),
    ]
    watches = _cards(Watch.objects.active())
    if strap.is_apple:
        watches = watches.filter(brand__slug="apple", mechanism="smart")
        watches = watches.filter(case_size__lte=42) if strap.fit == "apple_s" else watches.filter(case_size__gt=42)
    else:
        watches = watches.filter(lug_width=strap.width)
    related = (_strap_cards(Strap.objects.active()).exclude(pk=strap.pk)
               .filter(Q(width=strap.width) if strap.width else Q(fit=strap.fit)).order_by("-is_hit", "?")[:4])
    return render(request, "shop/strap_detail.html", {
        "strap": strap,
        "specs": [(k, v) for k, v in specs if v],
        "fits_watches": watches.order_by("-is_hit", "-sold")[:4],
        "related": related,
        "in_cart": Cart(request).quantity_of(strap),
        "regions": ch.REGIONS,
        "region_days": {key: ch.delivery_days(key) for key, _label in ch.REGIONS},
        "jsonld": seo.script(request, seo.product(request, strap), seo.breadcrumbs(request, [
            (_("Bosh sahifa"), reverse("shop:home")), (_("Tasmalar"), reverse("shop:straps")),
            (str(strap), None)])),
    })


@cache_control(public=True, max_age=60 * 60 * 24)
def watch_svg(request, slug):
    watch = get_object_or_404(Watch.objects.select_related("brand", "category").prefetch_related("features"),
                              slug=slug)
    return HttpResponse(render_watch(watch), content_type="image/svg+xml")


@cache_control(public=True, max_age=60 * 60 * 24)
def strap_svg(request, slug):
    strap = get_object_or_404(Strap.objects.select_related("brand"), slug=slug)
    return HttpResponse(render_strap(strap), content_type="image/svg+xml")


@cache_control(public=True, max_age=60 * 60 * 24)
def category_svg(request, slug):
    cat = get_object_or_404(Category, slug=slug)
    sample = (cat.watches.active().select_related("brand", "category").prefetch_related("features")
              .order_by("-is_hit", "-sold", "pk").first())
    svg = render_watch(sample) if sample else render_art(default_spec(cat.art_style, cat.name))
    return HttpResponse(svg, content_type="image/svg+xml")


def wishlist(request):
    ids = Wishlist(request).ids
    by_id = {w.pk: w for w in _cards(Watch.objects.active().filter(pk__in=ids))}
    return render(request, "shop/wishlist.html", {"watches": [by_id[i] for i in ids if i in by_id]})


@require_POST
def wishlist_toggle(request, pk):
    watch = get_object_or_404(Watch, pk=pk)
    wl = Wishlist(request)
    added = wl.toggle(watch.pk)
    if _is_ajax(request):
        return JsonResponse({"added": added, "count": len(wl),
                             "message": _("Sevimlilarga qo‘shildi") if added else _("Sevimlilardan olib tashlandi")})
    return redirect(request.POST.get("next") or watch.get_absolute_url())


def search_suggest(request):
    q = (request.GET.get("q") or "").strip()[:80]
    if len(q) < 2:
        return JsonResponse({"items": [], "total": 0, "straps_total": 0})
    watches, straps_qs = Watch.objects.active(), Strap.objects.active()
    for term in q.split():
        watches = watches.filter(Q(name__icontains=term) | Q(brand__name__icontains=term) | Q(sku__icontains=term)
                                 | Q(category__name__icontains=term) | Q(category__name_ru__icontains=term)
                                 | Q(category__name_en__icontains=term))
        straps_qs = straps_qs.filter(Q(name__icontains=term) | Q(name_ru__icontains=term)
                                     | Q(name_en__icontains=term) | Q(brand__name__icontains=term))
    watches = _cards(watches).order_by("-is_hit", "-sold")
    straps_qs = _strap_cards(straps_qs).order_by("-is_hit", "-sold")
    found = list(watches[:6])
    found += list(straps_qs[:6 - len(found)])
    return JsonResponse({
        "total": watches.count(),
        "straps_total": straps_qs.count(),
        "straps_url": reverse("shop:straps") + "?" + urlencode({"q": q}),
        "items": [{"title": p.local_name if p.kind == "strap" else p.name, "brand": p.brand.name,
                   "price": som(p.price), "old_price": som(p.old_price) if p.is_sale else "",
                   "url": p.get_absolute_url(), "img": p.image_url} for p in found],
    })


def info_page(template):
    def view(request):
        regions = [(label, ch.delivery_days(key)) for key, label in ch.REGIONS]
        return render(request, f"pages/{template}.html", {"region_days": regions})
    view.__name__ = f"page_{template}"
    return view


def robots_txt(request):
    lines = ["User-agent: *", "Disallow: /admin/"]
    for prefix in ("", "/ru", "/en"):
        for path in ("savat/", "rasmiylashtirish/", "buyurtma/", "sevimlilar/", "qidiruv/"):
            lines.append(f"Disallow: {prefix}/{path}")
    lines += ["", f"Sitemap: {request.build_absolute_uri(reverse('sitemap'))}"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


def page_not_found(request, exception=None):
    return render(request, "pages/404.html", status=404)
