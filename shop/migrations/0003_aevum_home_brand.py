"""Do‘kon nomi Aevum bo‘ldi: «O’clock Home» brendi «Aevum Home» ga, uning soatlari manzili ham yangilanadi."""
from django.db import migrations

OLD, NEW = ("O’clock Home", "oclock-home"), ("Aevum Home", "aevum-home")


def _rename(apps, src, dst):
    Brand = apps.get_model("shop", "Brand")
    Watch = apps.get_model("shop", "Watch")
    brand = Brand.objects.filter(slug=src[1]).first()
    if not brand or Brand.objects.filter(slug=dst[1]).exists():
        return
    brand.name, brand.slug = dst
    brand.save(update_fields=["name", "slug"])
    for watch in Watch.objects.filter(brand=brand, slug__startswith=src[1] + "-"):
        watch.slug = dst[1] + watch.slug[len(src[1]):]
        watch.save(update_fields=["slug"])


def forwards(apps, schema_editor):
    _rename(apps, OLD, NEW)


def backwards(apps, schema_editor):
    _rename(apps, NEW, OLD)


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0002_brand_country_en_brand_country_ru_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
