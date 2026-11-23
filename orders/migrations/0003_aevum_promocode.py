"""Do‘kon nomi Aevum bo‘ldi: OCLOCK10 promokodi AEVUM10 ga almashadi (chegirma va sozlamalari saqlanadi)."""
from django.db import migrations, models


def rename_promo(apps, schema_editor):
    PromoCode = apps.get_model("orders", "PromoCode")
    if not PromoCode.objects.filter(code="AEVUM10").exists():
        PromoCode.objects.filter(code="OCLOCK10").update(code="AEVUM10")


def restore_promo(apps, schema_editor):
    PromoCode = apps.get_model("orders", "PromoCode")
    if not PromoCode.objects.filter(code="OCLOCK10").exists():
        PromoCode.objects.filter(code="AEVUM10").update(code="OCLOCK10")


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_orderitem_strap_alter_callback_message_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='promocode',
            name='code',
            field=models.CharField(help_text='Katta harflarda, masalan AEVUM10', max_length=30, unique=True, verbose_name='Kod'),
        ),
        migrations.RunPython(rename_promo, restore_promo),
    ]
