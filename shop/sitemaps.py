"""sitemap.xml — qidiruv tizimlariga saytdagi barcha ochiq sahifalar ro‘yxati.

Har bir sahifa uch tilda (uz, /ru/, /en/) beriladi va hreflang bilan bog‘lanadi.
"""
from django.contrib.sitemaps import Sitemap
from django.db.models import Count, Q
from django.urls import reverse

from .models import Brand, Category, Strap, Watch


class I18nSitemap(Sitemap):
    i18n = True
    alternates = True
    x_default = True


class WatchSitemap(I18nSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Watch.objects.active().order_by("pk").only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


class StrapSitemap(I18nSitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Strap.objects.active().order_by("pk").only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(I18nSitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return Category.objects.annotate(n=Count("watches", filter=Q(watches__is_active=True))).filter(n__gt=0)


class BrandSitemap(I18nSitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return Brand.objects.annotate(n=Count("watches", filter=Q(watches__is_active=True))).filter(n__gt=0)


class PageSitemap(I18nSitemap):
    changefreq = "weekly"
    priorities = {"shop:home": 1.0, "shop:catalog": 0.9, "shop:sale": 0.9, "shop:unique": 0.8, "shop:new": 0.8,
                  "shop:straps": 0.8}

    def items(self):
        return ["shop:home", "shop:catalog", "shop:sale", "shop:unique", "shop:new", "shop:straps", "shop:brands",
                "shop:delivery", "shop:warranty", "shop:about", "shop:contacts", "shop:faq"]

    def location(self, name):
        return reverse(name)

    def priority(self, name):
        return self.priorities.get(name, 0.4)


SITEMAPS = {
    "pages": PageSitemap,
    "categories": CategorySitemap,
    "watches": WatchSitemap,
    "straps": StrapSitemap,
    "brands": BrandSitemap,
}
