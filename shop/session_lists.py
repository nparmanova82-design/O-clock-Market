"""Sessiyada saqlanadigan ro‘yxatlar: sevimlilar va yaqinda ko‘rilganlar (ro‘yxatdan o‘tish shart emas)."""

WISHLIST_KEY = "wishlist"
RECENT_KEY = "recent"
RECENT_LIMIT = 8


class SessionList:
    key = ""
    limit = None

    def __init__(self, request):
        self.session = request.session
        self.ids = [int(i) for i in self.session.get(self.key, []) if str(i).isdigit()]

    def _save(self):
        self.session[self.key] = self.ids

    def __contains__(self, pk):
        return pk in self.ids

    def __len__(self):
        return len(self.ids)


class Wishlist(SessionList):
    key = WISHLIST_KEY

    def toggle(self, pk):
        """Qo‘shadi yoki olib tashlaydi; qo‘shilgan bo‘lsa True qaytaradi."""
        if pk in self.ids:
            self.ids.remove(pk)
            added = False
        else:
            self.ids.insert(0, pk)
            added = True
        self._save()
        return added


class Recent(SessionList):
    key = RECENT_KEY

    def push(self, pk):
        self.ids = [pk] + [i for i in self.ids if i != pk][:RECENT_LIMIT - 1]
        self._save()
