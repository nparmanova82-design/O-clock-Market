"""locale/<til>/LC_MESSAGES/django.po → django.mo (GNU gettext o‘rnatilmagan bo‘lsa ham ishlaydi).

    python manage.py compile_translations

Render’da build.sh har deployda shuni ishga tushiradi, .mo fayllarni repoga qo‘shish shart emas.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from shop import po


class Command(BaseCommand):
    help = ".po tarjima fayllaridan .mo yasaydi"

    def handle(self, *args, **options):
        done = 0
        for lang, _name in settings.LANGUAGES:
            path = settings.BASE_DIR / "locale" / lang / "LC_MESSAGES" / "django.po"
            if not path.exists():
                continue
            entries = po.read_po(path)
            bad = [e.msgid for e in entries.values()
                   if e.msgid and e.translated and not all(po.same_vars(e.msgid, s) for s in e.msgstr[:1])]
            if bad:
                raise CommandError(f"{lang}: tarjimada %(...)s o‘zgaruvchilari mos emas: {bad[:5]}")
            n = po.write_mo(path.with_suffix(".mo"), lang, entries)
            missing = sum(1 for e in entries.values() if e.msgid and not e.translated)
            self.stdout.write(f"{lang}: {n} ta tarjima" + (f", {missing} ta tarjimasiz" if missing else ""))
            done += 1
        if not done:
            self.stdout.write("Tarjima fayllari topilmadi (locale/<til>/LC_MESSAGES/django.po).")
