import re

from django import forms
from django.utils.translation import gettext_lazy as _

from shop.choices import REGIONS

from .models import Callback, Order


def normalize_phone(value):
    """«90 123 45 67», «+998901234567» va h.k. → «+998 90 123 45 67»."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) != 12 or not digits.startswith("998"):
        raise forms.ValidationError(_("Telefon raqamini +998 90 123 45 67 ko‘rinishida kiriting."))
    return f"+{digits[:3]} {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:]}"


class PhoneField(forms.CharField):
    def clean(self, value):
        return normalize_phone(super().clean(value))


class CheckoutForm(forms.ModelForm):
    phone = PhoneField(label=_("Telefon"), widget=forms.TextInput(attrs={
        "placeholder": "+998 90 123 45 67", "inputmode": "tel", "autocomplete": "tel"}))
    region = forms.ChoiceField(label=_("Viloyat"), choices=[("", _("Tanlang"))] + REGIONS,
                               widget=forms.Select(attrs={"data-region-days": "#eta"}))
    payment = forms.ChoiceField(label=_("To‘lov usuli"), choices=Order.PAYMENTS, widget=forms.RadioSelect,
                                initial="cash")

    class Meta:
        model = Order
        fields = ["full_name", "phone", "region", "city", "address", "comment", "payment", "gift_wrap"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": _("Masalan, Aziza Karimova"), "autocomplete": "name"}),
            "city": forms.TextInput(attrs={"placeholder": _("Masalan, Chilonzor tumani")}),
            "address": forms.TextInput(attrs={"placeholder": _("Ko‘cha, uy, xonadon, mo‘ljal"),
                                              "autocomplete": "street-address"}),
            "comment": forms.Textarea(attrs={"rows": 3, "placeholder": _("Kuryer uchun izoh (ixtiyoriy)")}),
        }


class TrackForm(forms.Form):
    number = forms.CharField(label=_("Buyurtma raqami"), max_length=20,
                             widget=forms.TextInput(attrs={"placeholder": "OC-261113-1234"}))
    phone = PhoneField(label=_("Telefon"), widget=forms.TextInput(attrs={"placeholder": "+998 90 123 45 67",
                                                                      "inputmode": "tel"}))

    def clean_number(self):
        return self.cleaned_data["number"].strip().upper()


class CallbackForm(forms.ModelForm):
    phone = PhoneField(label=_("Telefon"), widget=forms.TextInput(attrs={"placeholder": "+998 90 123 45 67",
                                                                      "inputmode": "tel"}))

    class Meta:
        model = Callback
        fields = ["name", "phone", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Ismingiz")}),
            "message": forms.Textarea(attrs={"rows": 3, "placeholder": _("Savolingiz (ixtiyoriy)")}),
        }
