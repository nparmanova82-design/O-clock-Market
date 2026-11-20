from django.contrib import admin

from shop.utils import som

from .models import Callback, Order, OrderItem, PromoCode


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("watch", "strap", "title", "price", "quantity", "line_total")
    readonly_fields = ("line_total",)
    autocomplete_fields = ("watch", "strap")

    @admin.display(description="Summa")
    def line_total(self, obj):
        return som(obj.total) if obj.pk else "—"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "created_at", "full_name", "phone", "region", "payment", "total_som", "status")
    list_editable = ("status",)
    list_filter = ("status", "payment", "region", "created_at")
    search_fields = ("number", "full_name", "phone", "address")
    readonly_fields = ("number", "created_at", "updated_at", "subtotal", "discount", "delivery_cost", "total",
                       "promo_code")
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    fieldsets = (
        (None, {"fields": ("number", "status", "created_at", "updated_at")}),
        ("Mijoz", {"fields": ("full_name", "phone", "region", "city", "address", "comment")}),
        ("To‘lov", {"fields": ("payment", "gift_wrap", "promo_code", "subtotal", "discount", "delivery_cost",
                                "total")}),
    )

    @admin.display(description="Jami", ordering="total")
    def total_som(self, obj):
        return som(obj.total)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "percent", "min_total", "valid_until", "is_active")
    list_editable = ("is_active",)


@admin.register(Callback)
class CallbackAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "message", "created_at", "is_done")
    list_editable = ("is_done",)
    list_filter = ("is_done",)
