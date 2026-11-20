from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from shop.choices import REGIONS, delivery_days
from shop.models import Strap, Watch

from .cart import Cart, normalize_key
from .forms import CallbackForm, CheckoutForm, TrackForm
from .models import Order, OrderItem, PromoCode

MY_ORDERS_KEY = "my_orders"


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _back(request, fallback="orders:cart"):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
        return redirect(nxt)
    return redirect(fallback)


def _qty(request, default=1):
    try:
        return max(0, min(99, int(request.POST.get("quantity", default))))
    except (TypeError, ValueError):
        return default


def _cart_json(request, cart, message="", ok=True):
    return JsonResponse({"ok": ok, "count": len(cart), "message": message})


def cart_detail(request):
    cart = Cart(request)
    return render(request, "orders/cart.html", {"cart": cart, "quote": cart.quote(), "promo": cart.promo()})


def cart_drawer(request):
    cart = Cart(request)
    return render(request, "orders/_drawer.html", {"cart": cart, "quote": cart.quote()})


def _add(request, item):
    cart = Cart(request)
    before = cart.quantity_of(item)
    qty = cart.add(item, _qty(request))
    if not item.in_stock:
        msg, ok = _("Bu mahsulot hozir sotuvda yo‘q"), False
    elif qty == before:
        msg, ok = _("Omborda faqat %(n)s dona bor") % {"n": item.stock}, False
    else:
        msg, ok = _("«%(name)s» savatchaga qo‘shildi") % {"name": item}, True
    if _is_ajax(request):
        return _cart_json(request, cart, msg, ok)
    (messages.success if ok else messages.warning)(request, msg)
    return _back(request)


@require_POST
def cart_add(request, pk):
    return _add(request, get_object_or_404(Watch.objects.active(), pk=pk))


@require_POST
def cart_add_strap(request, pk):
    return _add(request, get_object_or_404(Strap.objects.active(), pk=pk))


def _item_by_key(key):
    key = normalize_key(key)
    if not key:
        raise Http404
    model = Watch if key[0] == "w" else Strap
    return get_object_or_404(model, pk=int(key[1:]))


@require_POST
def cart_update(request, key):
    cart = Cart(request)
    cart.add(_item_by_key(key), _qty(request), replace=True)
    if _is_ajax(request):
        return _cart_json(request, cart)
    return _back(request)


@require_POST
def cart_remove(request, key):
    cart = Cart(request)
    cart.remove(key)
    if _is_ajax(request):
        return _cart_json(request, cart, _("Savatchadan olib tashlandi"))
    return _back(request)


@require_POST
def promo_apply(request):
    code = (request.POST.get("code") or "").strip().upper()
    cart = Cart(request)
    promo = PromoCode.objects.filter(code=code).first() if code else None
    if promo and promo.is_valid:
        cart.set_promo(promo.code)
        messages.success(request, _("%(code)s promokodi qo‘llandi: −%(percent)s%%") % {
            "code": promo.code, "percent": promo.percent})
    else:
        cart.drop_promo()
        messages.error(request, _("Bunday promokod topilmadi yoki muddati tugagan"))
    return _back(request)


@require_POST
def promo_remove(request):
    Cart(request).drop_promo()
    return _back(request)


def checkout(request):
    cart = Cart(request)
    if not cart.lines():
        messages.info(request, _("Savatcha bo‘sh — avval soat tanlang"))
        return redirect("shop:catalog")

    form = CheckoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        order = _place_order(request, cart, form)
        if order:
            request.session[MY_ORDERS_KEY] = [order.number] + request.session.get(MY_ORDERS_KEY, [])[:19]
            return redirect("orders:success", number=order.number)
        return redirect("orders:cart")

    return render(request, "orders/checkout.html", {
        "form": form,
        "cart": cart,
        "quote": cart.quote(),
        "promo": cart.promo(),
        "region_days": {key: delivery_days(key) for key, _ in REGIONS},
    })


def _place_order(request, cart, form):
    """Ombordagi qoldiqni qulflab tekshiradi, buyurtmani yaratadi va qoldiqni kamaytiradi."""
    with transaction.atomic():
        lines = cart.lines()
        locked = {}
        for model in (Watch, Strap):
            ids = [ln["item"].pk for ln in lines if isinstance(ln["item"], model)]
            for obj in model.objects.select_for_update().select_related("brand").filter(pk__in=ids):
                locked[obj.cart_key] = obj
        problems = []
        for line in lines:
            item = locked.get(line["key"])
            if not item or not item.is_active or item.stock < line["quantity"]:
                problems.append(line)
        if problems:
            for line in problems:
                fresh = locked.get(line["key"])
                if fresh and fresh.stock:
                    cart.add(fresh, fresh.stock, replace=True)
                else:
                    cart.remove(line["key"])
            names = ", ".join(str(line["item"]) for line in problems)
            messages.error(request, _("Omborda yetarli emas: %(names)s. Savatchani tekshirib, qaytadan urinib "
                                      "ko‘ring.") % {"names": names})
            return None

        promo = cart.promo()
        quote = cart.quote()
        order = form.save(commit=False)
        order.subtotal = quote["subtotal"]
        order.discount = quote["discount"]
        order.delivery_cost = 0
        order.total = quote["total"]
        order.promo_code = promo.code if promo and quote["discount"] else ""
        order.save()
        for line in lines:
            item = locked[line["key"]]
            is_watch = isinstance(item, Watch)
            OrderItem.objects.create(order=order, watch=item if is_watch else None, strap=None if is_watch else item,
                                     title=str(item), price=item.price, quantity=line["quantity"])
            type(item).objects.filter(pk=item.pk).update(stock=F("stock") - line["quantity"],
                                                         sold=F("sold") + line["quantity"])
    cart.clear()
    return order


def success(request, number):
    if number not in request.session.get(MY_ORDERS_KEY, []):
        raise Http404
    order = get_object_or_404(Order.objects.prefetch_related("items__watch", "items__strap"), number=number)
    return render(request, "orders/success.html", {"order": order})


def track(request):
    form = TrackForm(request.GET or None)
    order = None
    searched = False
    if request.GET and form.is_valid():
        searched = True
        order = (Order.objects.prefetch_related("items")
                 .filter(number=form.cleaned_data["number"], phone=form.cleaned_data["phone"]).first())
    return render(request, "orders/track.html", {"form": form, "order": order, "searched": searched,
                                                 "steps": Order.STATUSES[:4]})


@require_POST
def callback(request):
    form = CallbackForm(request.POST)
    if form.is_valid():
        form.save()
        msg, ok = _("Rahmat! Operatorimiz tez orada qo‘ng‘iroq qiladi."), True
    else:
        msg, ok = " ".join(e for errs in form.errors.values() for e in errs), False
    if _is_ajax(request):
        return JsonResponse({"ok": ok, "message": msg})
    (messages.success if ok else messages.error)(request, msg)
    return _back(request, fallback=reverse("shop:contacts"))
