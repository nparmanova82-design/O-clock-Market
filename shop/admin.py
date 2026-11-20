from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Brand, Category, Feature, Strap, Watch
from .utils import som


TRANSLATION_NOTE = "Ruscha va inglizcha nusxa bo‘sh bo‘lsa, saytda o‘zbekchasi ko‘rsatiladi."


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "watch_count", "strap_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("name", "slug", "country", "description")}),
        ("Tarjima", {"fields": (("country_ru", "country_en"), "description_ru", "description_en"),
                     "description": TRANSLATION_NOTE, "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n=Count("watches", distinct=True),
                                                      ns=Count("straps", distinct=True))

    @admin.display(description="Soatlar", ordering="n")
    def watch_count(self, obj):
        return obj.n

    @admin.display(description="Tasmalar", ordering="ns")
    def strap_count(self, obj):
        return obj.ns


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_ru", "name_en", "art_style", "order", "watch_count")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("name", "slug", "short", "art_style", "order")}),
        ("Tarjima", {"fields": (("name_ru", "name_en"), "short_ru", "short_en"), "description": TRANSLATION_NOTE}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n=Count("watches"))

    @admin.display(description="Soatlar", ordering="n")
    def watch_count(self, obj):
        return obj.n


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("name", "name_ru", "name_en", "slug", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}


class SaleFilter(admin.SimpleListFilter):
    title = "aksiya"
    parameter_name = "aksiya"

    def lookups(self, request, model_admin):
        return [("1", "Aksiyada"), ("0", "Aksiyasiz")]

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.on_sale()
        if self.value() == "0":
            return queryset.exclude(pk__in=queryset.on_sale().values("pk"))
        return queryset


@admin.register(Watch)
class WatchAdmin(admin.ModelAdmin):
    list_display = ("thumb", "__str__", "category", "gender", "price", "old_price", "discount", "stock",
                    "is_new", "is_hit", "is_active")
    list_display_links = ("thumb", "__str__")
    list_editable = ("price", "old_price", "stock", "is_new", "is_hit", "is_active")
    list_filter = ("is_active", SaleFilter, "gender", "category", "brand", "mechanism", "is_new", "is_hit")
    search_fields = ("name", "brand__name", "sku")
    list_select_related = ("brand", "category")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("features",)
    readonly_fields = ("preview", "sold", "created_at", "updated_at")
    list_per_page = 50
    fieldsets = (
        (None, {"fields": ("preview", "brand", "category", "name", "slug", "sku", "gender", "is_active")}),
        ("Narx va ombor", {"fields": (("price", "old_price"), "stock", "warranty_months", ("is_new", "is_hit"),
                                      "sold")}),
        ("Xususiyatlar", {"fields": ("mechanism", ("case_size", "thickness"), "case_material",
                                     ("strap_material", "lug_width"), "glass", "water_resistance", "features",
                                     "description")}),
        ("Tarjima", {"fields": ("description_ru", "description_en"), "description": TRANSLATION_NOTE,
                     "classes": ("collapse",)}),
        ("Rasm", {"fields": ("image", "art_style", ("case_shape", "case_finish"), ("dial_color", "strap_color"),
                             "bezel_color"),
                  "description": "Surat yuklanmasa, sayt soat rasmini shu sozlamalar bo‘yicha o‘zi chizadi."}),
        ("Sana", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="")
    def thumb(self, obj):
        return format_html('<img src="{}" alt="" style="width:44px;height:44px;object-fit:contain">', obj.image_url)

    @admin.display(description="Rasm")
    def preview(self, obj):
        if not obj.pk:
            return "Saqlangandan keyin ko‘rinadi"
        return format_html('<img src="{}" alt="" style="width:220px;height:220px;object-fit:contain;'
                           'background:#efe3cd;border-radius:8px">', obj.image_url)

    @admin.display(description="Chegirma")
    def discount(self, obj):
        return f"−{obj.discount_percent}% ({som(obj.saving)})" if obj.is_sale else "—"


@admin.register(Strap)
class StrapAdmin(admin.ModelAdmin):
    list_display = ("thumb", "__str__", "material", "width", "fit", "color", "price", "old_price", "discount",
                    "stock", "is_new", "is_hit", "is_active")
    list_display_links = ("thumb", "__str__")
    list_editable = ("price", "old_price", "stock", "is_new", "is_hit", "is_active")
    list_filter = ("is_active", SaleFilter, "material", "width", "fit", "buckle", "brand", "is_new", "is_hit")
    search_fields = ("name", "name_ru", "name_en", "brand__name", "sku")
    list_select_related = ("brand",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("preview", "sold", "created_at", "updated_at")
    list_per_page = 50
    fieldsets = (
        (None, {"fields": ("preview", "brand", "name", "slug", "sku", "is_active")}),
        ("Narx va ombor", {"fields": (("price", "old_price"), "stock", ("is_new", "is_hit"), "sold")}),
        ("Xususiyatlar", {"fields": ("material", "color", "finish", ("width", "fit"), "buckle", "description"),
                          "description": "Kenglik — soatning «Tasma kengligi» bilan bir xil bo‘lsa, tasma soat "
                                         "sahifasida «Mos tasmalar» qatorida chiqadi."}),
        ("Tarjima", {"fields": (("name_ru", "name_en"), "description_ru", "description_en"),
                     "description": TRANSLATION_NOTE}),
        ("Rasm", {"fields": ("image",), "description": "Surat yuklanmasa, sayt tasma rasmini o‘zi chizadi."}),
        ("Sana", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="")
    def thumb(self, obj):
        return format_html('<img src="{}" alt="" style="width:44px;height:44px;object-fit:contain">', obj.image_url)

    @admin.display(description="Rasm")
    def preview(self, obj):
        if not obj.pk:
            return "Saqlangandan keyin ko‘rinadi"
        return format_html('<img src="{}" alt="" style="width:220px;height:220px;object-fit:contain;'
                           'background:#efe3cd;border-radius:8px">', obj.image_url)

    @admin.display(description="Chegirma")
    def discount(self, obj):
        return f"−{obj.discount_percent}% ({som(obj.saving)})" if obj.is_sale else "—"
