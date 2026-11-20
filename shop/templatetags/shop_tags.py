from django import template

from ..utils import som as _som

register = template.Library()


@register.filter
def som(value):
    return _som(value)


@register.filter
def num(value):
    """Faqat raqam: 1250000 → «1 250 000»."""
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return value


@register.simple_tag(takes_context=True)
def url_with(context, **kwargs):
    """Joriy GET parametrlarini saqlab, berilganlarini almashtiradi (sahifalash uchun)."""
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else "?"


@register.filter
def in_list(value, items):
    return value in items


class StashNode(template.Node):
    """{% stash "nom" %}…{% endstash %} — ichini chiqaradi va keyin {% unstash "nom" %} uchun eslab qoladi.

    Bitta blok mazmunini <title> va og:title kabi bir necha joyda ishlatish uchun
    (Django bir xil nomli blokni ikki marta yozishga ruxsat bermaydi).
    """

    def __init__(self, name, nodelist):
        self.name, self.nodelist = name, nodelist

    def render(self, context):
        text = " ".join(self.nodelist.render(context).split())
        context.render_context.setdefault("stash", {})[self.name] = text
        return text


@register.tag
def stash(parser, token):
    _, name = token.split_contents()
    nodelist = parser.parse(("endstash",))
    parser.delete_first_token()
    return StashNode(name.strip("\"'"), nodelist)


@register.simple_tag(takes_context=True)
def unstash(context, name):
    from django.utils.safestring import mark_safe

    return mark_safe(context.render_context.get("stash", {}).get(name, ""))


@register.filter
def mul(value, arg):
    try:
        return int(value) * int(arg)
    except (TypeError, ValueError):
        return ""
