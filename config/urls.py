from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from shop.sitemaps import SITEMAPS
from shop.views import robots_txt

admin.site.site_header = "O’clock market — boshqaruv"
admin.site.site_title = "O’clock market"
admin.site.index_title = "Do‘kon boshqaruvi"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("", include("shop.art_urls")),
]

# O‘zbekcha — prefikssiz (/katalog/), ruscha — /ru/katalog/, inglizcha — /en/katalog/
urlpatterns += i18n_patterns(
    path("", include("orders.urls")),
    path("", include("shop.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "shop.views.page_not_found"
