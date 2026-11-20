"""Saytdagi barcha tarjima qilinadigan matnlarni yig‘ib, locale/<til>/LC_MESSAGES/django.po ga yozadi.

    python manage.py make_translations

Mavjud tarjimalar saqlanadi, yangi matnlar bo‘sh msgstr bilan qo‘shiladi, ishlatilmay qolganlari o‘chiriladi.
Keyin .po faylda tarjimalarni yozing va `python manage.py compile_translations` ni ishga tushiring.
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.template import engines

from shop import po


class Command(BaseCommand):
    help = "Tarjima matnlarini yig‘ib, .po fayllarni yangilaydi (GNU gettext shart emas)"

    def handle(self, *args, **options):
        engine = engines["django"].engine
        items = po.collect(settings.BASE_DIR, engine)
        order, refs = [], {}
        for msgid, plural, ref in items:
            key = (msgid, plural)
            if key not in refs:
                order.append(key)
                refs[key] = []
            refs[key].append(ref)

        for lang, _name in settings.LANGUAGES:
            if lang == settings.LANGUAGE_CODE:
                continue
            path = settings.BASE_DIR / "locale" / lang / "LC_MESSAGES" / "django.po"
            old = po.read_po(path)
            entries, new = [], 0
            for key in order:
                prev = old.get(key)
                n = po.NPLURALS[lang] if key[1] else 1
                entry = po.Entry(key[0], key[1], (prev.msgstr if prev else [""] * n)[:n], refs[key],
                                 prev.fuzzy if prev else False)
                entry.msgstr += [""] * (n - len(entry.msgstr))
                new += prev is None
                entries.append(entry)
            dropped = len([k for k in old if k[0] and k not in refs])
            po.write_po(path, lang, entries)
            missing = sum(not e.translated for e in entries)
            self.stdout.write(f"{lang}: {len(entries)} ta matn, {new} ta yangi, {dropped} ta o‘chirildi, "
                              f"{missing} ta tarjimasiz: {path.relative_to(settings.BASE_DIR)}")
