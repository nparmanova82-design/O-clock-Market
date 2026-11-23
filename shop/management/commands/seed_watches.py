"""Katalogni boshlang‘ich ma’lumotlar bilan to‘ldiradi.

    python manage.py seed_watches          # katalog bo‘sh bo‘lsa — to‘ldiradi; bor bo‘lsa — faqat yetishmaganini
                                           # (ruscha/inglizcha nomlar, tasma kengligi, tasmalar) qo‘shadi
    python manage.py seed_watches --reset  # soatlar, tasmalar, brendlar va turlarni o‘chirib, qaytadan yaratadi

Narxlar so‘mda va taxminiy — admin paneldan o‘zgartiring.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone, translation
from django.utils.text import slugify

from orders.models import PromoCode
from shop.models import Brand, Category, Feature, Strap, Watch

CATEGORIES = [
    ("klassik", "Klassik soatlar", "Kostyum va kundalik kiyimga mos nafis modellar.", "classic"),
    ("sport", "Sport soatlari", "Mustahkam korpus, yorqin indekslar va suvga chidamlilik.", "sport"),
    ("gavvos", "G‘avvos soatlari", "200 metrgacha suvga chidamli, aylanuvchi bezelli soatlar.", "diver"),
    ("uchuvchi", "Uchuvchi soatlari", "Katta raqamlar va uzoqdan ham o‘qiladigan siferblat.", "pilot"),
    ("xronograf", "Xronograflar", "Sekundomer funksiyali soatlar.", "chrono"),
    ("hashamatli", "Hashamatli soatlar", "Shveysariya mexanizmlari va qimmatbaho materiallar.", "luxury"),
    ("harbiy", "Harbiy (field) soatlar", "Oddiy, ishonchli va 24 soatlik shkalali soatlar.", "field"),
    ("smart", "Smart soatlar", "Qadam, puls, xabarnomalar va kontaktsiz to‘lov.", "smart"),
    ("raqamli", "Elektron soatlar", "Budilnik, sekundomer va yoritgichli raqamli soatlar.", "digital"),
    ("bolalar", "Bolalar soatlari", "Yorqin ranglar, yengil korpus va oson o‘qiladigan raqamlar.", "kids"),
    ("chontak", "Cho‘ntak soatlari", "Zanjirli klassik soatlar — esda qoladigan sovg‘a.", "pocket"),
    ("devor", "Devor soatlari", "Uy va ofis uchun ovozsiz mexanizmli soatlar.", "wall"),
    ("stol", "Stol soatlari", "Kamin, javon va ish stoli uchun soatlar.", "table"),
    ("budilnik", "Budilniklar", "Qo‘ng‘iroqli klassik budilniklar.", "alarm"),
]

FEATURES = [
    ("sana", "Sana ko‘rsatkichi"),
    ("xronograf", "Xronograf (sekundomer)"),
    ("budilnik", "Budilnik"),
    ("yoritgich", "Yoritgich / lyuminofor"),
    ("shaffof", "Shaffof orqa qopqoq"),
    ("gmt", "GMT — ikkinchi vaqt mintaqasi"),
    ("zarb", "Zarbaga chidamli"),
    ("gps", "GPS"),
    ("puls", "Puls o‘lchash"),
    ("nfc", "NFC to‘lov"),
    ("xabar", "Xabarnomalar"),
    ("ovozsiz", "Ovozsiz mexanizm"),
]

BRANDS = [
    ("Casio", "Yaponiya", "Elektron soatlar va G-Shock seriyasi bilan mashhur."),
    ("Seiko", "Yaponiya", "1881-yildan beri soat ishlab chiqaradi, o‘z mexanizmlari bilan."),
    ("Citizen", "Yaponiya", "Yorug‘likdan quvvat oladigan Eco-Drive texnologiyasi muallifi."),
    ("Orient", "Yaponiya", "Hamyonbop avtomatik soatlar."),
    ("Tissot", "Shveysariya", "Le Locle shahridan, 1853-yildan beri."),
    ("Hamilton", "Shveysariya", "Amerika ildizlariga ega harbiy va uchuvchi soatlari."),
    ("Longines", "Shveysariya", "Nafislik va an’ana — 1832-yildan beri."),
    ("Swatch", "Shveysariya", "Rang-barang va hazilkash dizayn."),
    ("Rolex", "Shveysariya", "Hashamatli soatlarning eng taniqli nomi."),
    ("Omega", "Shveysariya", "Seamaster va Speedmaster seriyalari."),
    ("Fossil", "AQSh", "Vintaj ruhidagi kundalik soatlar."),
    ("Timex", "AQSh", "Oddiy, chidamli va hamyonbop."),
    ("Michael Kors", "AQSh", "Moda soatlari, ayniqsa ayollar uchun."),
    ("Daniel Wellington", "Shvetsiya", "Minimalistik dizayn va ingichka korpus."),
    ("Laco", "Germaniya", "1925-yildan beri uchuvchi soatlari."),
    ("Vostok", "Rossiya", "Afsonaviy «Amfibiya» g‘avvos soati."),
    ("Apple", "AQSh", "iPhone bilan to‘liq integratsiyalashgan smart soatlar."),
    ("Samsung", "Janubiy Koreya", "Galaxy Watch — Android uchun smart soatlar."),
    ("Garmin", "AQSh", "Sport va sayohat uchun GPS soatlar."),
    ("Xiaomi", "Xitoy", "Hamyonbop smart soatlar."),
    ("Huawei", "Xitoy", "Uzoq ishlaydigan batareyali smart soatlar."),
    ("Flik Flak", "Shveysariya", "Swatch guruhining bolalar soatlari."),
    ("Elari", "Rossiya", "GPS-trekerli bolalar smart soatlari."),
    ("Charles-Hubert", "Fransiya", "Klassik cho‘ntak soatlari."),
    ("Hermle", "Germaniya", "Mexanik stol va devor soatlari, 1922-yildan beri."),
    ("Rhythm", "Yaponiya", "Devor soatlari va budilniklar."),
    ("Aevum Home", "O‘zbekiston", "Do‘konimizning uy va ofis uchun soatlari."),
]


def W(brand, cat, name, price, **kw):
    return dict(brand=brand, cat=cat, name=name, price=price, **kw)


WATCHES = [
    # — Klassik —
    W("Orient", "klassik", "Bambino 38", 2_650_000, old=3_100_000, g="unique", mech="automatic", size=38, thick=12.5,
      water=30, dial="cream", strap_c="brown", hit=True,
      desc="Gumbazsimon oyna va toza siferblat — 1950-yillar ruhidagi klassika."),
    W("Seiko", "klassik", "Presage Cocktail Time", 5_900_000, mech="automatic", size=40, thick=11.8, water=50,
      feats=["sana", "shaffof"], dial="blue", strap_c="black", hit=True,
      desc="Kokteyl ranglaridan ilhomlangan quyosh nurli siferblat."),
    W("Daniel Wellington", "klassik", "Classic 36 Sheffield", 1_750_000, old=2_190_000, g="unique", size=36,
      thick=6, water=30, finish="rose", dial="white", strap_c="black"),
    W("Tissot", "klassik", "Everytime 40", 3_400_000, strap="mesh", glass="sapphire", size=40, thick=7.5, water=30,
      feats=["sana"], dial="black", strap_c="metal", new=True),
    W("Citizen", "klassik", "Eco-Drive Classic", 2_900_000, mech="solar", strap="bracelet", size=40, water=100,
      feats=["sana"], dial="silver", strap_c="metal"),
    W("Longines", "klassik", "DolceVita", 21_500_000, g="women", glass="sapphire", size=23, water=30,
      shape="rect", dial="silver", strap_c="black"),
    W("Longines", "klassik", "Evidenza", 24_800_000, g="women", mech="automatic", glass="sapphire", size=26,
      water=30, shape="tonneau", finish="rose", dial="pink", strap_c="pink", new=True),
    W("Fossil", "klassik", "Carlie Mini", 1_450_000, old=1_790_000, g="women", size=28, water=50, finish="rose",
      dial="pink", strap_c="pink"),
    W("Michael Kors", "klassik", "Darci", 2_300_000, old=2_900_000, g="women", case="gold", strap="bracelet",
      size=39, water=50, finish="gold", dial="champagne", strap_c="metal"),
    W("Tissot", "klassik", "Le Locle Powermatic 80", 7_900_000, mech="automatic", glass="sapphire", size=39,
      water=30, feats=["sana", "shaffof"], dial="white", strap_c="brown", new=True,
      desc="80 soatlik quvvat zaxirasi — dam olish kunlari yechib qo‘ysangiz ham to‘xtamaydi."),
    W("Swatch", "klassik", "Sistem51 Irony", 2_100_000, g="unique", mech="automatic", glass="mineral", size=42,
      water=30, feats=["sana", "shaffof"], dial="blue", strap_c="navy"),
    W("Citizen", "klassik", "Eco-Drive Ladies", 2_450_000, old=2_850_000, g="women", mech="solar",
      strap="bracelet", size=30, water=50, finish="rose", dial="white", strap_c="metal"),
    W("Casio", "klassik", "Sheen Classic", 1_250_000, g="women", strap="bracelet", size=34, water=50,
      feats=["sana"], finish="gold", dial="white", strap_c="metal"),

    # — Sport —
    W("Casio", "sport", "G-Shock GA-2100", 1_690_000, old=1_990_000, g="unique", case="resin", strap="rubber",
      size=45, thick=11.8, water=200, feats=["yoritgich", "budilnik", "xronograf", "zarb"], shape="octagon",
      finish="black", dial="black", strap_c="black", hit=True,
      desc="Ingichka sakkiz qirrali korpus va karbon himoya — zarbaga chidamli G-Shock."),
    W("Seiko", "sport", "5 Sports SRPD", 3_200_000, mech="automatic", strap="bracelet", size=42, water=100,
      feats=["sana", "shaffof"], dial="blue", strap_c="metal", bezel="black", hit=True),
    W("Tissot", "sport", "PRX 40 Powermatic 80", 9_400_000, mech="automatic", strap="bracelet", glass="sapphire",
      size=40, thick=10.9, water=100, feats=["sana", "shaffof"], shape="octagon", dial="blue", strap_c="metal",
      hit=True, new=True, desc="Integratsiyalashgan braslet va «vafli» naqshli siferblat."),
    W("Tissot", "sport", "PRX 35", 6_200_000, old=6_900_000, g="unique", strap="bracelet", glass="sapphire",
      size=35, water=100, feats=["sana"], shape="octagon", dial="green", strap_c="metal"),
    W("Citizen", "sport", "Tsuyosa", 3_900_000, g="unique", mech="automatic", strap="bracelet", glass="sapphire",
      size=40, water=50, feats=["sana"], dial="blue", strap_c="metal", new=True),

    # — G‘avvos —
    W("Seiko", "gavvos", "Prospex Turtle", 6_800_000, mech="automatic", strap="rubber", size=45, thick=13.4,
      water=200, feats=["sana", "yoritgich"], dial="black", bezel="black", strap_c="black", hit=True),
    W("Citizen", "gavvos", "Promaster Diver Eco-Drive", 3_600_000, old=4_200_000, mech="solar", strap="rubber",
      size=44, water=200, feats=["sana", "yoritgich"], dial="blue", bezel="blue", strap_c="navy"),
    W("Orient", "gavvos", "Kamasu", 3_900_000, mech="automatic", strap="bracelet", glass="sapphire", size=42,
      water=200, feats=["sana", "yoritgich"], dial="green", bezel="green", strap_c="metal"),
    W("Vostok", "gavvos", "Amphibia", 1_300_000, old=1_500_000, mech="automatic", strap="rubber", glass="acrylic",
      size=41, water=200, feats=["sana", "yoritgich"], dial="blue", bezel="blue", strap_c="black",
      desc="Sovet davridan beri deyarli o‘zgarmagan, sodda va chidamli g‘avvos soati."),
    W("Rolex", "gavvos", "Submariner Date", 165_000_000, mech="automatic", strap="bracelet", glass="sapphire",
      size=41, water=300, feats=["sana", "yoritgich"], dial="black", bezel="black", strap_c="metal",
      warranty=60, stock=1),
    W("Omega", "gavvos", "Seamaster Diver 300M", 72_000_000, mech="automatic", strap="bracelet", glass="sapphire",
      size=42, water=300, feats=["sana", "yoritgich", "shaffof"], dial="blue", bezel="blue", strap_c="metal",
      warranty=60, stock=2),
    W("Seiko", "gavvos", "5 Sports GMT", 4_300_000, mech="automatic", strap="bracelet", size=42, water=100,
      feats=["sana", "gmt"], dial="black", bezel="pepsi", strap_c="metal", new=True),

    # — Uchuvchi —
    W("Hamilton", "uchuvchi", "Khaki Aviation Pilot Day Date", 10_900_000, mech="automatic", glass="sapphire",
      size=42, water=100, feats=["sana"], dial="black", strap_c="brown", hit=True),
    W("Laco", "uchuvchi", "Augsburg 42", 7_500_000, mech="automatic", glass="sapphire", size=42, water=50,
      dial="black", strap_c="tan", desc="Ikkinchi jahon urushi davridagi B-Uhr uchuvchi soatlari uslubida."),
    W("Orient", "uchuvchi", "Flight", 2_200_000, old=2_600_000, mech="automatic", strap="nylon", size=42,
      water=100, feats=["sana"], dial="black", strap_c="olive"),

    # — Xronograf —
    W("Casio", "xronograf", "Edifice EFV-540", 1_950_000, old=2_350_000, strap="bracelet", size=46, water=100,
      feats=["sana", "xronograf"], dial="black", strap_c="metal"),
    W("Seiko", "xronograf", "Speedtimer Solar", 8_400_000, mech="solar", strap="bracelet", glass="sapphire",
      size=39, water=100, feats=["xronograf", "sana"], dial="white", strap_c="metal", new=True),
    W("Tissot", "xronograf", "Chrono XL Classic", 5_300_000, glass="sapphire", size=45, water=100,
      feats=["sana", "xronograf"], dial="black", strap_c="brown", hit=True),
    W("Fossil", "xronograf", "Grant Chronograph", 2_200_000, old=2_750_000, size=44, water=50,
      feats=["xronograf"], dial="white", strap_c="brown"),
    W("Citizen", "xronograf", "Eco-Drive Titanium Chrono", 3_800_000, mech="solar", case="titanium",
      strap="bracelet", glass="sapphire", size=42, water=100, feats=["xronograf", "sana"], finish="titanium",
      dial="grey", strap_c="metal"),
    W("Omega", "xronograf", "Speedmaster Professional", 88_000_000, mech="mechanical", strap="bracelet",
      glass="sapphire", size=42, water=50, feats=["xronograf"], dial="black", strap_c="metal", warranty=60,
      stock=1, desc="Qo‘lda buraladigan xronograf — Oyga borgan soat avlodidan."),

    # — Hashamatli —
    W("Rolex", "hashamatli", "Datejust 36", 135_000_000, g="unique", mech="automatic", strap="bracelet",
      glass="sapphire", size=36, water=100, feats=["sana"], dial="blue", strap_c="metal", warranty=60, stock=1),
    W("Omega", "hashamatli", "Constellation 29", 68_000_000, g="women", case="gold", strap="bracelet",
      glass="sapphire", size=29, water=50, feats=["sana"], finish="gold", dial="champagne", strap_c="metal",
      warranty=60, stock=2),
    W("Longines", "hashamatli", "Master Collection", 26_000_000, mech="automatic", glass="sapphire", size=40,
      water=30, feats=["sana", "shaffof"], dial="silver", strap_c="brown", warranty=24),

    # — Harbiy —
    W("Hamilton", "harbiy", "Khaki Field Mechanical", 7_200_000, g="unique", mech="mechanical", strap="nylon",
      glass="sapphire", size=38, water=50, dial="black", strap_c="olive", hit=True,
      desc="Qo‘lda buraladigan, 80 soat quvvat zaxirali dala soati."),
    W("Timex", "harbiy", "Expedition Scout", 1_150_000, old=1_390_000, size=40, water=50,
      feats=["sana", "yoritgich"], dial="cream", strap_c="brown"),
    W("Seiko", "harbiy", "5 Sports Field", 3_100_000, mech="automatic", strap="nylon", size=39, water=100,
      feats=["sana"], dial="green", strap_c="olive", new=True),

    # — Smart —
    W("Apple", "smart", "Watch SE 44 mm", 3_900_000, g="unique", mech="smart", case="aluminium",
      strap="silicone", glass="glass", size=44, water=50, feats=["puls", "gps", "nfc", "xabar"], shape="rect",
      finish="black", dial="black", strap_c="black", hit=True),
    W("Apple", "smart", "Watch Ultra 49 mm", 11_900_000, g="unique", mech="smart", case="titanium",
      strap="nylon", glass="sapphire", size=49, water=100, feats=["puls", "gps", "nfc", "xabar", "zarb"],
      shape="rect", finish="titanium", dial="black", strap_c="orange", new=True),
    W("Samsung", "smart", "Galaxy Watch 44 mm", 3_800_000, old=4_400_000, g="unique", mech="smart",
      case="aluminium", strap="silicone", glass="sapphire", size=44, water=50,
      feats=["puls", "gps", "nfc", "xabar"], finish="steel", dial="black", strap_c="grey"),
    W("Garmin", "smart", "Forerunner 265", 5_900_000, g="unique", mech="smart", case="resin", strap="silicone",
      glass="glass", size=46, water=50, feats=["puls", "gps", "xabar"], finish="black", dial="black",
      strap_c="sky"),
    W("Xiaomi", "smart", "Redmi Watch 5", 1_200_000, old=1_450_000, g="unique", mech="smart", case="aluminium",
      strap="silicone", glass="glass", size=46, water=50, feats=["puls", "gps", "xabar"], shape="rect",
      finish="black", dial="black", strap_c="mint"),
    W("Huawei", "smart", "Watch GT 5 46 mm", 3_400_000, mech="smart", strap="leather", glass="glass", size=46,
      water=50, feats=["puls", "gps", "xabar", "nfc"], finish="steel", dial="black", strap_c="brown", new=True),

    # — Elektron —
    W("Casio", "raqamli", "F-91W", 260_000, g="unique", mech="digital", case="resin", strap="rubber",
      glass="acrylic", size=35, water=10, feats=["budilnik", "xronograf", "yoritgich"], shape="rect",
      finish="black", dial="black", strap_c="black", hit=True,
      desc="Dunyodagi eng mashhur elektron soatlardan biri: batareyasi 7 yilgacha yetadi."),
    W("Casio", "raqamli", "A168 Vintage", 520_000, g="unique", mech="digital", strap="bracelet", glass="acrylic",
      size=38, water=10, feats=["budilnik", "xronograf", "yoritgich"], shape="rect", finish="steel",
      dial="black", strap_c="metal"),
    W("Casio", "raqamli", "G-Shock DW-5600", 1_150_000, g="unique", mech="digital", case="resin", strap="rubber",
      size=43, water=200, feats=["budilnik", "xronograf", "yoritgich", "zarb"], shape="rect", finish="black",
      dial="black", strap_c="black", hit=True),
    W("Casio", "raqamli", "W-218H", 330_000, g="unique", mech="digital", case="resin", strap="rubber",
      glass="acrylic", size=43, water=50, feats=["budilnik", "xronograf", "yoritgich"], shape="rect",
      finish="black", dial="black", strap_c="navy", new=True),
    W("Timex", "raqamli", "Ironman Classic 30", 750_000, old=890_000, g="unique", mech="digital", case="resin",
      strap="rubber", glass="acrylic", size=38, water=100, feats=["xronograf", "budilnik", "yoritgich"],
      shape="octagon", finish="black", dial="black", strap_c="grey"),

    # — Bolalar —
    W("Flik Flak", "bolalar", "Tick Tock Sky", 690_000, g="kids", case="resin", strap="silicone", glass="acrylic",
      size=31, water=30, finish="white", dial="white", strap_c="sky", new=True),
    W("Flik Flak", "bolalar", "Pink Stars", 690_000, old=820_000, g="kids", case="resin", strap="silicone",
      glass="acrylic", size=31, water=30, finish="white", dial="white", strap_c="pink"),
    W("Timex", "bolalar", "Time Machines", 520_000, g="kids", case="resin", strap="nylon", glass="acrylic",
      size=29, water=30, finish="white", dial="white", strap_c="red"),
    W("Casio", "bolalar", "LW-204 Kids", 380_000, g="kids", mech="digital", case="resin", strap="rubber",
      glass="acrylic", size=38, water=100, feats=["budilnik", "xronograf", "yoritgich"], shape="rect",
      finish="white", dial="black", strap_c="yellow", art="digital"),
    W("Elari", "bolalar", "KidPhone 4G", 1_100_000, old=1_300_000, g="kids", mech="smart", case="resin",
      strap="silicone", glass="glass", size=44, water=30, feats=["gps", "xabar"], shape="rect", finish="white",
      dial="black", strap_c="mint", desc="Bolangiz qayerdaligini xaritada ko‘rasiz, unga qo‘ng‘iroq qila olasiz."),

    # — Cho‘ntak —
    W("Charles-Hubert", "chontak", "Gold Hunter", 1_450_000, g="unique", mech="mechanical", case="gold",
      strap="chain", size=47, water=0, finish="gold", dial="cream", strap_c="metal", hit=True,
      desc="Zanjiri bilan birga — bobosidan nevarasiga o‘tadigan sovg‘a."),
    W("Charles-Hubert", "chontak", "Railroad Silver", 1_050_000, old=1_290_000, g="unique", strap="chain",
      size=47, water=0, finish="steel", dial="white", strap_c="metal"),
    W("Charles-Hubert", "chontak", "Black Skeleton", 1_690_000, g="unique", mech="mechanical", strap="chain",
      size=48, water=0, finish="black", dial="black", strap_c="metal", new=True),

    # — Devor —
    W("Aevum Home", "devor", "Oak 40 sm", 690_000, g="home", case="wood", strap="none", glass="glass",
      size=400, water=0, feats=["ovozsiz"], finish="wood", dial="white", strap_c="metal", hit=True),
    W("Aevum Home", "devor", "Nordic Black 30 sm", 420_000, old=520_000, g="home", case="aluminium",
      strap="none", glass="glass", size=300, water=0, feats=["ovozsiz"], finish="black", dial="white",
      strap_c="black"),
    W("Aevum Home", "devor", "Cream Minimal 35 sm", 480_000, g="home", case="resin", strap="none",
      glass="glass", size=350, water=0, feats=["ovozsiz"], finish="white", dial="cream", strap_c="white",
      new=True),
    W("Aevum Home", "devor", "Vokzal 45 sm", 890_000, g="home", case="aluminium", strap="none", glass="glass",
      size=450, water=0, feats=["ovozsiz"], finish="steel", dial="black", strap_c="metal"),

    # — Stol —
    W("Aevum Home", "stol", "Kamin Walnut", 890_000, g="home", case="wood", strap="none", glass="glass",
      size=160, water=0, feats=["ovozsiz"], finish="wood", dial="cream", strap_c="metal", hit=True),
    W("Hermle", "stol", "Mantel Westminster", 6_900_000, g="home", mech="mechanical", case="wood", strap="none",
      glass="glass", size=180, water=0, finish="wood", dial="champagne", strap_c="metal", new=True,
      desc="Har chorak soatda Westminster kuyini chaladigan mexanik kamin soati."),
    W("Aevum Home", "stol", "Desk Mint", 390_000, old=450_000, g="home", case="resin", strap="none",
      glass="glass", size=120, water=0, feats=["ovozsiz"], finish="white", dial="white", strap_c="mint"),

    # — Budilnik —
    W("Rhythm", "budilnik", "Twin Bell Classic", 350_000, g="home", strap="none", glass="glass", size=110,
      water=0, feats=["budilnik", "yoritgich"], finish="steel", dial="white", strap_c="red", hit=True),
    W("Aevum Home", "budilnik", "Retro Mint", 290_000, old=340_000, g="home", strap="none", glass="glass",
      size=100, water=0, feats=["budilnik"], finish="steel", dial="white", strap_c="mint"),
    W("Aevum Home", "budilnik", "Black Bell", 320_000, g="home", strap="none", glass="glass", size=100,
      water=0, feats=["budilnik"], finish="gold", dial="cream", strap_c="black", new=True),
]

INTRO = {
    "klassik": "Nafis klassik soat: ofisga ham, bayramga ham mos keladi.",
    "sport": "Faol hayot uchun mustahkam sport soati.",
    "gavvos": "Suv ostida ham ishonchli g‘avvos soati: aylanuvchi bezel sho‘ng‘ish vaqtini o‘lchaydi.",
    "uchuvchi": "Uchuvchilar uchun yaratilgan uslub: katta raqamlar bir qarashda o‘qiladi.",
    "xronograf": "Xronograf — sekundomerli soat: tugmalar bilan vaqtni o‘lchaysiz.",
    "hashamatli": "Avloddan avlodga o‘tadigan hashamatli soat.",
    "harbiy": "Harbiy soatlar an’anasidagi sodda va chidamli model.",
    "smart": "Smart soat telefoningiz bilan ulanadi: qo‘ng‘iroq va xabarlar bilakda ko‘rinadi.",
    "raqamli": "Elektron soat: yoritgich, budilnik va sekundomer — hammasi bir joyda.",
    "bolalar": "Bolalar uchun yengil va yorqin soat — vaqtni o‘rganishga yordam beradi.",
    "chontak": "Klassik cho‘ntak soati zanjiri bilan.",
    "devor": "Devor soati uy yoki ofis interyerini to‘ldiradi.",
    "stol": "Stol soati javon, kamin yoki ish stoliga.",
    "budilnik": "Qo‘ng‘irog‘i baland klassik budilnik — ertalab uyg‘onmay qolmaysiz.",
}
INTRO_I18N = {
    "ru": {
        "klassik": "Изящные классические часы: подходят и для офиса, и для праздника.",
        "sport": "Прочные спортивные часы для активной жизни.",
        "gavvos": "Надёжные дайверские часы: вращающийся безель отмеряет время погружения.",
        "uchuvchi": "Стиль, созданный для пилотов: крупные цифры читаются с одного взгляда.",
        "xronograf": "Хронограф — часы с секундомером: время замеряется кнопками.",
        "hashamatli": "Роскошные часы, которые передаются из поколения в поколение.",
        "harbiy": "Простая и выносливая модель в традициях армейских часов.",
        "smart": "Смарт-часы подключаются к телефону: звонки и сообщения видны на запястье.",
        "raqamli": "Электронные часы: подсветка, будильник и секундомер — всё в одном.",
        "bolalar": "Лёгкие и яркие детские часы — помогают научиться понимать время.",
        "chontak": "Классические карманные часы с цепочкой.",
        "devor": "Настенные часы дополнят интерьер дома или офиса.",
        "stol": "Настольные часы для полки, камина или рабочего стола.",
        "budilnik": "Классический громкий будильник — утром точно не проспите.",
    },
    "en": {
        "klassik": "An elegant classic watch that suits the office and special occasions alike.",
        "sport": "A tough sports watch for an active life.",
        "gavvos": "A dependable diver’s watch: the rotating bezel times your dive.",
        "uchuvchi": "A style made for pilots: large numerals read at a glance.",
        "xronograf": "A chronograph is a watch with a stopwatch: time events with the pushers.",
        "hashamatli": "A luxury watch to pass down from generation to generation.",
        "harbiy": "A simple, rugged model in the military watch tradition.",
        "smart": "The smartwatch connects to your phone: calls and messages show up on your wrist.",
        "raqamli": "A digital watch: backlight, alarm and stopwatch all in one.",
        "bolalar": "A light, bright watch for kids that helps them learn to tell time.",
        "chontak": "A classic pocket watch with a chain.",
        "devor": "A wall clock to complete your home or office interior.",
        "stol": "A desk clock for a shelf, mantelpiece or work desk.",
        "budilnik": "A loud classic alarm clock — you won’t oversleep.",
    },
}
MECH_TEXT = {
    "automatic": "Avtomatik mexanizm qo‘l harakatidan o‘zi buraladi — batareya kerak emas.",
    "mechanical": "Qo‘lda buraladigan mexanik soat — an’anaviy soatsozlik namunasi.",
    "quartz": "Kvarts mexanizmi juda aniq yuradi, batareyasi 2–3 yil yetadi.",
    "solar": "Yorug‘likdan quvvat oladi — batareya almashtirish shart emas.",
    "kinetic": "Kinetik mexanizm harakatdan quvvat yig‘adi.",
    "digital": "Elektron mexanizm, batareyasi bir necha yil yetadi.",
    "smart": "Batareya bir quvvatlashda bir necha kun ishlaydi.",
}
MECH_I18N = {
    "ru": {
        "automatic": "Автоматический механизм заводится сам от движения руки — батарейка не нужна.",
        "mechanical": "Механические часы с ручным заводом — образец традиционного часового дела.",
        "quartz": "Кварцевый механизм очень точен, батарейки хватает на 2–3 года.",
        "solar": "Заряжаются от света — менять батарейку не нужно.",
        "kinetic": "Кинетический механизм накапливает энергию от движения.",
        "digital": "Электронный механизм, батарейки хватает на несколько лет.",
        "smart": "Одного заряда батареи хватает на несколько дней.",
    },
    "en": {
        "automatic": "The automatic movement winds itself as you move — no battery needed.",
        "mechanical": "A hand-wound mechanical watch — a piece of traditional watchmaking.",
        "quartz": "The quartz movement is very accurate; the battery lasts 2–3 years.",
        "solar": "Powered by light — no battery changes needed.",
        "kinetic": "The kinetic movement stores energy from motion.",
        "digital": "A digital movement whose battery lasts several years.",
        "smart": "One charge lasts several days.",
    },
}
DESC_I18N = {
    "Gumbazsimon oyna va toza siferblat — 1950-yillar ruhidagi klassika.": (
        "Выпуклое стекло и чистый циферблат — классика в духе 1950-х.",
        "A domed crystal and a clean dial — a classic in the spirit of the 1950s."),
    "Kokteyl ranglaridan ilhomlangan quyosh nurli siferblat.": (
        "Циферблат с эффектом «солнечных лучей», вдохновлённый цветами коктейлей.",
        "A sunburst dial inspired by the colours of cocktails."),
    "80 soatlik quvvat zaxirasi — dam olish kunlari yechib qo‘ysangiz ham to‘xtamaydi.": (
        "Запас хода 80 часов — не остановятся, даже если снять их на выходные.",
        "An 80-hour power reserve — it keeps running even if you take it off for the weekend."),
    "Ingichka sakkiz qirrali korpus va karbon himoya — zarbaga chidamli G-Shock.": (
        "Тонкий восьмигранный корпус с карбоновой защитой — ударопрочный G-Shock.",
        "A slim octagonal case with carbon protection — a shock-resistant G-Shock."),
    "Integratsiyalashgan braslet va «vafli» naqshli siferblat.": (
        "Интегрированный браслет и циферблат с «вафельным» узором.",
        "An integrated bracelet and a “waffle” patterned dial."),
    "Sovet davridan beri deyarli o‘zgarmagan, sodda va chidamli g‘avvos soati.": (
        "Простые и выносливые дайверские часы, почти не изменившиеся с советских времён.",
        "A simple, tough diver’s watch that has barely changed since Soviet times."),
    "Ikkinchi jahon urushi davridagi B-Uhr uchuvchi soatlari uslubida.": (
        "В стиле лётных часов B-Uhr времён Второй мировой войны.",
        "In the style of the World War II B-Uhr pilot watches."),
    "Qo‘lda buraladigan xronograf — Oyga borgan soat avlodidan.": (
        "Хронограф с ручным заводом — из рода часов, побывавших на Луне.",
        "A hand-wound chronograph from the family of the watch that went to the Moon."),
    "Qo‘lda buraladigan, 80 soat quvvat zaxirali dala soati.": (
        "Полевые часы с ручным заводом и запасом хода 80 часов.",
        "A hand-wound field watch with an 80-hour power reserve."),
    "Dunyodagi eng mashhur elektron soatlardan biri: batareyasi 7 yilgacha yetadi.": (
        "Одни из самых известных электронных часов в мире: батарейки хватает до 7 лет.",
        "One of the most famous digital watches in the world: the battery lasts up to 7 years."),
    "Bolangiz qayerdaligini xaritada ko‘rasiz, unga qo‘ng‘iroq qila olasiz.": (
        "Вы видите на карте, где ваш ребёнок, и можете ему позвонить.",
        "See where your child is on the map and call them."),
    "Zanjiri bilan birga — bobosidan nevarasiga o‘tadigan sovg‘a.": (
        "Вместе с цепочкой — подарок, который переходит от деда к внуку.",
        "Complete with its chain — a gift passed from grandfather to grandson."),
    "Har chorak soatda Westminster kuyini chaladigan mexanik kamin soati.": (
        "Механические каминные часы, которые каждые четверть часа играют мелодию Вестминстера.",
        "A mechanical mantel clock that plays the Westminster chime every quarter hour."),
}
SPEC_TEXT = {
    "uz": ("Korpus: {case}, {size} mm; oyna: {glass}.",
           "{w} metrgacha suvga chidamli — suzishda ham taqish mumkin.",
           "{w} metrgacha suvga chidamli: yomg‘ir va qo‘l yuvishdan qo‘rqmaydi.",
           "Suvdan ehtiyot qiling.",
           "Unique: dizayni erkak va ayolga birdek mos."),
    "ru": ("Корпус: {case}, {size} мм; стекло: {glass}.",
           "Водозащита до {w} метров — можно плавать.",
           "Водозащита до {w} метров: не боится дождя и мытья рук.",
           "Берегите от воды.",
           "Unique: дизайн одинаково подходит мужчинам и женщинам."),
    "en": ("Case: {case}, {size} mm; crystal: {glass}.",
           "Water resistant to {w} metres — fine for swimming.",
           "Water resistant to {w} metres: rain and hand washing are no problem.",
           "Keep away from water.",
           "Unique: the design suits men and women alike."),
}

# — Tarjimalar: turlar, funksiyalar, brendlar —
CATEGORY_I18N = {  # slug: (nomi ru, qisqa ru, nomi en, qisqa en)
    "klassik": ("Классические часы", "Изящные модели под костюм и на каждый день.",
                "Classic watches", "Elegant models for a suit or everyday wear."),
    "sport": ("Спортивные часы", "Прочный корпус, яркие индексы и водозащита.",
              "Sports watches", "Tough cases, bright indices and water resistance."),
    "gavvos": ("Дайверские часы", "Водозащита до 200 метров и вращающийся безель.",
               "Diver watches", "Water resistant to 200 metres with a rotating bezel."),
    "uchuvchi": ("Авиационные часы", "Крупные цифры и циферблат, который читается издалека.",
                 "Pilot watches", "Large numerals and a dial that reads from afar."),
    "xronograf": ("Хронографы", "Часы с функцией секундомера.", "Chronographs", "Watches with a stopwatch."),
    "hashamatli": ("Роскошные часы", "Швейцарские механизмы и драгоценные материалы.",
                   "Luxury watches", "Swiss movements and precious materials."),
    "harbiy": ("Армейские (field) часы", "Простые, надёжные, с 24-часовой шкалой.",
               "Field watches", "Simple, reliable and with a 24-hour scale."),
    "smart": ("Смарт-часы", "Шаги, пульс, уведомления и бесконтактная оплата.",
              "Smartwatches", "Steps, heart rate, notifications and contactless payments."),
    "raqamli": ("Электронные часы", "Цифровые часы с будильником, секундомером и подсветкой.",
                "Digital watches", "Digital watches with alarm, stopwatch and backlight."),
    "bolalar": ("Детские часы", "Яркие цвета, лёгкий корпус и понятные цифры.",
                "Kids’ watches", "Bright colours, light cases and easy-to-read numbers."),
    "chontak": ("Карманные часы", "Классика на цепочке — запоминающийся подарок.",
                "Pocket watches", "A classic on a chain — a memorable gift."),
    "devor": ("Настенные часы", "Часы с бесшумным механизмом для дома и офиса.",
              "Wall clocks", "Silent-movement clocks for home and office."),
    "stol": ("Настольные часы", "Часы для камина, полки и рабочего стола.",
             "Desk clocks", "Clocks for the mantelpiece, shelf and desk."),
    "budilnik": ("Будильники", "Классические будильники со звонком.", "Alarm clocks", "Classic bell alarm clocks."),
}
FEATURE_I18N = {
    "sana": ("Индикатор даты", "Date display"),
    "xronograf": ("Хронограф (секундомер)", "Chronograph (stopwatch)"),
    "budilnik": ("Будильник", "Alarm"),
    "yoritgich": ("Подсветка / люминофор", "Backlight / luminous"),
    "shaffof": ("Прозрачная задняя крышка", "Exhibition case back"),
    "gmt": ("GMT — второй часовой пояс", "GMT — second time zone"),
    "zarb": ("Ударопрочные", "Shock resistant"),
    "gps": ("GPS", "GPS"),
    "puls": ("Пульсометр", "Heart rate"),
    "nfc": ("NFC-оплата", "NFC payments"),
    "xabar": ("Уведомления", "Notifications"),
    "ovozsiz": ("Бесшумный механизм", "Silent movement"),
}
COUNTRY_I18N = {  # uz: (ru, en)
    "Yaponiya": ("Япония", "Japan"), "Shveysariya": ("Швейцария", "Switzerland"), "AQSh": ("США", "USA"),
    "Shvetsiya": ("Швеция", "Sweden"), "Germaniya": ("Германия", "Germany"), "Rossiya": ("Россия", "Russia"),
    "Janubiy Koreya": ("Южная Корея", "South Korea"), "Xitoy": ("Китай", "China"), "Fransiya": ("Франция", "France"),
    "O‘zbekiston": ("Узбекистан", "Uzbekistan"), "Avstriya": ("Австрия", "Austria"), "Italiya": ("Италия", "Italy"),
}
BRAND_DESC_I18N = {  # nomi: (tavsif ru, tavsif en)
    "Casio": ("Знаменит электронными часами и серией G-Shock.", "Famous for digital watches and the G-Shock line."),
    "Seiko": ("Делает часы с 1881 года, на собственных механизмах.", "Making watches since 1881, with in-house movements."),
    "Citizen": ("Автор технологии Eco-Drive — питания от света.", "Creator of Eco-Drive, the light-powered technology."),
    "Orient": ("Доступные автоматические часы.", "Affordable automatic watches."),
    "Tissot": ("Из города Ле-Локль, с 1853 года.", "From Le Locle, since 1853."),
    "Hamilton": ("Армейские и авиационные часы с американскими корнями.", "Military and pilot watches with American roots."),
    "Longines": ("Изящество и традиции — с 1832 года.", "Elegance and tradition since 1832."),
    "Swatch": ("Яркий и озорной дизайн.", "Colourful, playful design."),
    "Rolex": ("Самое известное имя среди роскошных часов.", "The best-known name in luxury watches."),
    "Omega": ("Серии Seamaster и Speedmaster.", "The Seamaster and Speedmaster lines."),
    "Fossil": ("Повседневные часы в винтажном духе.", "Everyday watches with a vintage spirit."),
    "Timex": ("Простые, выносливые и доступные.", "Simple, tough and affordable."),
    "Michael Kors": ("Модные часы, особенно женские.", "Fashion watches, especially for women."),
    "Daniel Wellington": ("Минималистичный дизайн и тонкий корпус.", "Minimalist design and a slim case."),
    "Laco": ("Авиационные часы с 1925 года.", "Pilot watches since 1925."),
    "Vostok": ("Легендарные дайверские часы «Амфибия».", "The legendary Amphibia diver’s watch."),
    "Apple": ("Смарт-часы, полностью интегрированные с iPhone.", "Smartwatches fully integrated with iPhone."),
    "Samsung": ("Galaxy Watch — смарт-часы для Android.", "Galaxy Watch — smartwatches for Android."),
    "Garmin": ("GPS-часы для спорта и путешествий.", "GPS watches for sport and travel."),
    "Xiaomi": ("Доступные смарт-часы.", "Affordable smartwatches."),
    "Huawei": ("Смарт-часы с долгоиграющей батареей.", "Smartwatches with long battery life."),
    "Flik Flak": ("Детские часы группы Swatch.", "Kids’ watches from the Swatch group."),
    "Elari": ("Детские смарт-часы с GPS-трекером.", "Kids’ smartwatches with a GPS tracker."),
    "Charles-Hubert": ("Классические карманные часы.", "Classic pocket watches."),
    "Hermle": ("Механические настольные и настенные часы с 1922 года.", "Mechanical desk and wall clocks since 1922."),
    "Rhythm": ("Настенные часы и будильники.", "Wall clocks and alarm clocks."),
    "Aevum Home": ("Часы нашего магазина для дома и офиса.", "Our store’s own clocks for home and office."),
    "Hirsch": ("Ремешки из кожи и каучука с 1765 года.", "Leather and rubber straps since 1765."),
    "Barton": ("Силиконовые и нейлоновые ремешки с быстросъёмными шпильками.",
               "Silicone and nylon straps with quick-release spring bars."),
    "Bonetto Cinturini": ("Каучуковые ремешки для дайверских часов.", "Rubber straps for diver watches."),
    "Di-Modell": ("Ремешки и браслеты на любую ширину.", "Straps and bracelets in every width."),
}
STRAP_BRANDS = [
    ("Hirsch", "Avstriya", "1765-yildan beri charm va kauchuk tasmalar."),
    ("Barton", "AQSh", "Tez yechiladigan shpilkali silikon va neylon tasmalar."),
    ("Bonetto Cinturini", "Italiya", "G‘avvos soatlari uchun kauchuk tasmalar."),
    ("Di-Modell", "Germaniya", "Har qanday kenglikdagi tasma va brasletlar."),
]

# — Tasma kengligi (mm). Integratsiyalashgan braslet, o‘z ulagichli smart va plastik korpuslarda — yo‘q —
LUG_WIDTHS = {
    "Tissot Le Locle Powermatic 80": 19, "Swatch Sistem51 Irony": 20, "Vostok Amphibia": 18,
    "Rolex Submariner Date": 21, "Omega Seamaster Diver 300M": 20, "Laco Augsburg 42": 20,
    "Omega Speedmaster Professional": 20, "Rolex Datejust 36": 20, "Samsung Galaxy Watch 44 mm": 20,
    "Garmin Forerunner 265": 22, "Citizen Promaster Diver Eco-Drive": 20,
}
NO_LUGS = {"Tissot PRX 40 Powermatic 80", "Tissot PRX 35", "Citizen Tsuyosa", "Omega Constellation 29",
           "Xiaomi Redmi Watch 5"}


def lug_width(d):
    key = f"{d['brand']} {d['name']}"
    if key in LUG_WIDTHS:
        return LUG_WIDTHS[key]
    if (key in NO_LUGS or d["cat"] in ("devor", "stol", "budilnik", "chontak") or d["brand"] == "Apple"
            or d.get("case") == "resin" or d.get("strap") == "none"):
        return None
    size = d.get("size", 40)
    for limit, width in ((26, 12), (29, 14), (33, 16), (37, 18), (40, 20)):
        if size <= limit:
            return width
    return 22


# — Tasmalar —
def S(brand, name, ru, en, price, material, color, width, fit, buckle, **kw):
    return dict(brand=brand, name=name, ru=ru, en=en, price=price, material=material, color=color, width=width,
                fit=fit, buckle=buckle, **kw)


STRAPS = [
    S("Hirsch", "Duke charm tasma", "Кожаный ремешок Duke", "Duke leather strap", 690_000, "leather", "brown", 20,
      "quick", "pin", old=820_000, hit=True),
    S("Hirsch", "Duke charm tasma", "Кожаный ремешок Duke", "Duke leather strap", 690_000, "leather", "black", 18,
      "quick", "pin"),
    S("Hirsch", "Liberty charm tasma", "Кожаный ремешок Liberty", "Liberty leather strap", 590_000, "leather",
      "tan", 16, "pins", "pin", finish="gold", new=True),
    S("Hirsch", "Grand Duke charm tasma", "Кожаный ремешок Grand Duke", "Grand Duke leather strap", 950_000,
      "leather", "navy", 22, "quick", "deployant"),
    S("Hirsch", "Lady charm tasma", "Женский кожаный ремешок Lady", "Lady leather strap", 520_000, "leather",
      "pink", 14, "pins", "pin", finish="rose"),
    S("Hirsch", "Petite charm tasma", "Кожаный ремешок Petite", "Petite leather strap", 490_000, "leather", "white",
      12, "pins", "pin", finish="gold", old=560_000),
    S("Hirsch", "Pure kauchuk tasma", "Каучуковый ремешок Pure", "Pure rubber strap", 1_150_000, "rubber", "black",
      22, "pins", "pin", hit=True),
    S("Di-Modell", "Pilot charm tasma", "Кожаный ремешок Pilot", "Pilot leather strap", 560_000, "leather", "brown",
      24, "pins", "pin"),
    S("Barton", "Elite silikon tasma", "Силиконовый ремешок Elite", "Elite silicone strap", 320_000, "silicone",
      "olive", 20, "quick", "pin", finish="black", old=390_000),
    S("Barton", "Elite silikon tasma", "Силиконовый ремешок Elite", "Elite silicone strap", 320_000, "silicone",
      "orange", 22, "quick", "pin"),
    S("Barton", "Elite silikon tasma", "Силиконовый ремешок Elite", "Elite silicone strap", 320_000, "silicone",
      "sky", 20, "quick", "pin", new=True),
    S("Barton", "Canvas neylon tasma", "Нейлоновый ремешок Canvas", "Canvas nylon strap", 280_000, "nylon", "olive",
      20, "quick", "pin"),
    S("Di-Modell", "NATO neylon tasma", "Нейлоновый ремешок NATO", "NATO nylon strap", 190_000, "nylon", "navy", 20,
      "pins", "pin", old=240_000, hit=True),
    S("Di-Modell", "NATO neylon tasma", "Нейлоновый ремешок NATO", "NATO nylon strap", 190_000, "nylon", "grey", 22,
      "pins", "pin", finish="black"),
    S("Di-Modell", "NATO neylon tasma", "Нейлоновый ремешок NATO", "NATO nylon strap", 190_000, "nylon", "red", 18,
      "pins", "pin"),
    S("Bonetto Cinturini", "300D kauchuk tasma", "Каучуковый ремешок 300D", "300D rubber strap", 480_000, "rubber",
      "black", 22, "pins", "pin", hit=True),
    S("Bonetto Cinturini", "284 kauchuk tasma", "Каучуковый ремешок 284", "284 rubber strap", 450_000, "rubber",
      "navy", 20, "pins", "pin"),
    S("Bonetto Cinturini", "282 kauchuk tasma", "Каучуковый ремешок 282", "282 rubber strap", 450_000, "rubber",
      "black", 24, "pins", "pin", new=True),
    S("Di-Modell", "Oyster po‘lat braslet", "Стальной браслет Oyster", "Oyster steel bracelet", 890_000, "bracelet",
      "metal", 20, "pins", "fold"),
    S("Di-Modell", "Jubilee braslet", "Браслет Jubilee", "Jubilee bracelet", 980_000, "bracelet", "metal", 20,
      "pins", "fold", finish="gold", new=True),
    S("Di-Modell", "Oyster po‘lat braslet", "Стальной браслет Oyster", "Oyster steel bracelet", 890_000, "bracelet",
      "metal", 22, "pins", "fold", old=1_050_000),
    S("Daniel Wellington", "Milan to‘ri", "Миланская сетка", "Milanese mesh strap", 650_000, "mesh", "metal", 18,
      "quick", "fold", finish="rose"),
    S("Di-Modell", "Milan to‘ri, magnitli", "Миланская сетка с магнитом", "Magnetic Milanese mesh", 450_000, "mesh",
      "metal", 20, "quick", "magnet", old=560_000),
    S("Samsung", "Sport silikon tasma", "Силиконовый ремешок Sport", "Sport silicone band", 390_000, "silicone",
      "grey", 20, "quick", "pin"),
    S("Garmin", "QuickFit 22 silikon tasma", "Силиконовый ремешок QuickFit 22", "QuickFit 22 silicone band",
      550_000, "silicone", "black", 22, "quick", "pin"),
    S("Apple", "Sport Band", "Спортивный ремешок Sport Band", "Sport Band", 650_000, "silicone", "white", None,
      "apple_l", "pin", hit=True),
    S("Apple", "Sport Loop", "Ремешок Sport Loop", "Sport Loop", 650_000, "nylon", "mint", None, "apple_s", "loop",
      new=True),
    S("Apple", "Milanese Loop", "Миланский браслет Milanese Loop", "Milanese Loop", 1_250_000, "mesh", "metal",
      None, "apple_l", "magnet"),
    S("Apple", "Solo Loop", "Монобраслет Solo Loop", "Solo Loop", 650_000, "silicone", "red", None, "apple_s",
      "loop"),
    S("Barton", "Apple Watch uchun silikon tasma", "Силиконовый ремешок для Apple Watch",
      "Silicone band for Apple Watch", 290_000, "silicone", "black", None, "apple_l", "pin", old=350_000),
]
STRAP_TEXT = {  # material: (uz, ru, en)
    "leather": ("Tabiiy charm: vaqt o‘tishi bilan yumshab, bilak shakliga moslashadi.",
                "Натуральная кожа: со временем становится мягче и принимает форму запястья.",
                "Genuine leather that softens over time and moulds to your wrist."),
    "bracelet": ("Zanglamas po‘lat braslet: bo‘g‘imlarini olib, uzunligini moslash mumkin.",
                 "Браслет из нержавеющей стали: длину можно подогнать, убрав звенья.",
                 "Stainless steel bracelet: remove links to adjust the length."),
    "mesh": ("Milan to‘ri — ingichka po‘lat to‘qima, istalgan uzunlikka moslanadi.",
             "Миланская сетка — тонкое стальное плетение, подгоняется под любую длину.",
             "Milanese mesh — a fine woven steel band that adjusts to any length."),
    "rubber": ("Tabiiy kauchuk: suv, ter va issiqdan qo‘rqmaydi — g‘avvos va sport soatlari uchun.",
               "Натуральный каучук: не боится воды, пота и жары — для дайверских и спортивных часов.",
               "Natural rubber that shrugs off water, sweat and heat — made for diver and sports watches."),
    "silicone": ("Yumshoq silikon: yengil, yuviladi va sport uchun qulay.",
                 "Мягкий силикон: лёгкий, моется и удобен для спорта.",
                 "Soft silicone: light, washable and comfortable for sport."),
    "nylon": ("Mustahkam neylon: yengil, tez quriydi va soatni bilakda ishonchli ushlaydi.",
              "Прочный нейлон: лёгкий, быстро сохнет и надёжно держит часы на запястье.",
              "Tough nylon: light, quick-drying and keeps the watch secure on your wrist."),
}
FIT_TEXT = {
    "pins": ("To‘plamda shpilkalar bor.", "Шпильки в комплекте.", "Spring bars included."),
    "quick": ("Tez yechiladigan shpilkalar — asbobsiz almashtiriladi.",
              "Быстросъёмные шпильки — замена без инструментов.", "Quick-release spring bars — swap without tools."),
    "apple_s": ("Apple Watch 38, 40, 41 va 42 mm uchun.", "Для Apple Watch 38, 40, 41 и 42 мм.",
                "For Apple Watch 38, 40, 41 and 42 mm."),
    "apple_l": ("Apple Watch 44, 45, 46 va 49 mm uchun.", "Для Apple Watch 44, 45, 46 и 49 мм.",
                "For Apple Watch 44, 45, 46 and 49 mm."),
}
LANGS = ("uz", "ru", "en")


def describe(watch, custom="", lang="uz"):
    """Soat tavsifi tanlangan tilda (uz — asosiy, ru/en — description_ru/description_en uchun)."""
    with translation.override(lang):
        intro = (INTRO if lang == "uz" else INTRO_I18N[lang]).get(watch.category.slug, "")
        mech = (MECH_TEXT if lang == "uz" else MECH_I18N[lang]).get(watch.mechanism, "")
        if custom and lang != "uz":
            custom = DESC_I18N.get(custom, ("", ""))[LANGS.index(lang) - 1]
        spec, deep, shallow, dry, uniq = SPEC_TEXT[lang]
        parts = [custom, intro, mech]
        if watch.strap_material != "none":
            parts.append(spec.format(case=str(watch.get_case_material_display()).lower(), size=watch.case_size,
                                     glass=str(watch.get_glass_display()).lower()))
        if watch.water_resistance >= 100:
            parts.append(deep.format(w=watch.water_resistance))
        elif watch.water_resistance >= 30:
            parts.append(shallow.format(w=watch.water_resistance))
        elif watch.strap_material != "none":
            parts.append(dry)
        if watch.gender == "unique":
            parts.append(uniq)
    return " ".join(p for p in parts if p)


def describe_strap(d, lang):
    i = LANGS.index(lang)
    return " ".join([STRAP_TEXT[d["material"]][i], FIT_TEXT[d["fit"]][i]])


def _fill(obj, **values):
    """Faqat bo‘sh maydonlarni to‘ldiradi (admin paneldagi tahrirlar saqlanadi). O‘zgargan bo‘lsa True."""
    changed = [k for k, v in values.items() if v not in (None, "") and getattr(obj, k) in (None, "")]
    for k in changed:
        setattr(obj, k, values[k])
    if changed:
        obj.save(update_fields=changed)
    return bool(changed)


def _brand_i18n(name, country):
    c_ru, c_en = COUNTRY_I18N.get(country, ("", ""))
    d_ru, d_en = BRAND_DESC_I18N.get(name, ("", ""))
    return {"country_ru": c_ru, "country_en": c_en, "description_ru": d_ru, "description_en": d_en}


class Command(BaseCommand):
    help = "Katalogni boshlang‘ich soatlar, tasmalar, brendlar va turlar bilan to‘ldiradi"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Avval katalogni tozalaydi")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            Strap.objects.all().delete()
            Watch.objects.all().delete()
            Brand.objects.all().delete()
            Category.objects.all().delete()
            Feature.objects.all().delete()
        if Watch.objects.exists():
            # Katalog bor: faqat yetishmaganini qo‘shadi (tarjimalar, tasma kengligi, tasmalar)
            n = self.fill_missing()
            self.stdout.write(f"Katalog allaqachon to‘ldirilgan — {n} ta yozuv to‘ldirildi (--reset bilan qaytadan).")
            return

        cats = {}
        for i, (slug, name, short, art) in enumerate(CATEGORIES):
            ru, short_ru, en, short_en = CATEGORY_I18N[slug]
            cats[slug], _ = Category.objects.update_or_create(slug=slug, defaults={
                "name": name, "short": short, "art_style": art, "order": i, "name_ru": ru, "short_ru": short_ru,
                "name_en": en, "short_en": short_en})
        feats = {}
        for i, (slug, name) in enumerate(FEATURES):
            ru, en = FEATURE_I18N[slug]
            feats[slug], _ = Feature.objects.update_or_create(slug=slug, defaults={
                "name": name, "order": i, "name_ru": ru, "name_en": en})
        brands = {}
        for name, country, desc in BRANDS + STRAP_BRANDS:
            brands[name], _ = Brand.objects.update_or_create(
                slug=slugify(name.replace("’", "")),
                defaults={"name": name, "country": country, "description": desc, **_brand_i18n(name, country)})

        now = timezone.now()
        total = len(WATCHES)
        for i, d in enumerate(WATCHES):
            brand = brands[d["brand"]]
            watch = Watch(
                brand=brand, category=cats[d["cat"]], name=d["name"],
                slug=slugify(f"{brand.slug} {d['name']}"),
                sku=d.get("sku") or f"OC-{1001 + i}",
                gender=d.get("g", "men"), mechanism=d.get("mech", "quartz"),
                case_material=d.get("case", "steel"), strap_material=d.get("strap", "leather"),
                lug_width=lug_width(d),
                glass=d.get("glass", "mineral"), case_size=d.get("size", 40), thickness=d.get("thick"),
                water_resistance=d.get("water", 50), price=d["price"], old_price=d.get("old"),
                stock=d.get("stock", 6 + (i * 7) % 15),
                warranty_months=d.get("warranty", 24 if d["cat"] == "hashamatli" else 12),
                is_new=d.get("new", False), is_hit=d.get("hit", False),
                art_style=d.get("art", ""), case_shape=d.get("shape", "round"),
                case_finish=d.get("finish", "steel"), dial_color=d.get("dial", "black"),
                strap_color=d.get("strap_c", "black"), bezel_color=d.get("bezel", ""),
            )
            watch.save()
            watch.features.set([feats[f] for f in d.get("feats", [])])
            texts = {f"description{'' if lang == 'uz' else '_' + lang}": describe(watch, d.get("desc", ""), lang)
                     for lang in LANGS}
            # yangi kelganlar oxirida qo‘shilgandek ko‘rinsin; xitlar ko‘proq sotilgan
            age = timedelta(days=3 + (i * 5) % 40) if not watch.is_new else timedelta(hours=i)
            Watch.objects.filter(pk=watch.pk).update(
                **texts, created_at=now - age, sold=(120 if watch.is_hit else 0) + (total - i) * 3 % 47)

        self.create_straps(brands)
        PromoCode.objects.get_or_create(code="AEVUM10", defaults={"percent": 10})
        PromoCode.objects.get_or_create(code="SOVGA15", defaults={"percent": 15, "min_total": 3_000_000})
        self.stdout.write(self.style.SUCCESS(
            f"Tayyor: {Watch.objects.count()} ta soat, {Strap.objects.count()} ta tasma, "
            f"{Brand.objects.count()} ta brend, {Category.objects.count()} ta tur. Promokodlar: AEVUM10, SOVGA15."))

    def create_straps(self, brands):
        now = timezone.now()
        for i, d in enumerate(STRAPS):
            brand = brands[d["brand"]]
            size = f"{d['width']}mm" if d["width"] else d["fit"].replace("_", "-")
            strap = Strap.objects.create(
                brand=brand, name=d["name"], name_ru=d["ru"], name_en=d["en"],
                slug=slugify(f"{brand.slug} {d['en']} {d['color']} {size}"), sku=f"OS-{2001 + i}",
                material=d["material"], color=d["color"], finish=d.get("finish", "steel"), width=d["width"],
                fit=d["fit"], buckle=d["buckle"], price=d["price"], old_price=d.get("old"),
                stock=d.get("stock", 8 + (i * 5) % 17), is_new=d.get("new", False), is_hit=d.get("hit", False),
                description=describe_strap(d, "uz"), description_ru=describe_strap(d, "ru"),
                description_en=describe_strap(d, "en"))
            age = timedelta(days=2 + (i * 3) % 30) if not strap.is_new else timedelta(hours=i)
            Strap.objects.filter(pk=strap.pk).update(created_at=now - age,
                                                     sold=(80 if strap.is_hit else 0) + (i * 7) % 31)

    def fill_missing(self):
        n = 0
        for slug, _name, _short, _art in CATEGORIES:
            cat = Category.objects.filter(slug=slug).first()
            if cat:
                ru, short_ru, en, short_en = CATEGORY_I18N[slug]
                n += _fill(cat, name_ru=ru, short_ru=short_ru, name_en=en, short_en=short_en)
        for slug, _name in FEATURES:
            feat = Feature.objects.filter(slug=slug).first()
            if feat:
                ru, en = FEATURE_I18N[slug]
                n += _fill(feat, name_ru=ru, name_en=en)
        brands = {}
        for name, country, desc in BRANDS + STRAP_BRANDS:
            brand, created = Brand.objects.get_or_create(
                slug=slugify(name.replace("’", "")), defaults={"name": name, "country": country, "description": desc})
            brands[name] = brand
            n += created + _fill(brand, **_brand_i18n(brand.name, brand.country))
        by_slug = {}
        for d in WATCHES:
            by_slug[slugify(f"{slugify(d['brand'].replace('’', ''))} {d['name']}")] = d
        for watch in Watch.objects.select_related("category"):
            d = by_slug.get(watch.slug)
            if not d:
                continue
            n += _fill(watch, lug_width=lug_width(d), description_ru=describe(watch, d.get("desc", ""), "ru"),
                       description_en=describe(watch, d.get("desc", ""), "en"))
        if not Strap.objects.exists():
            self.create_straps(brands)
            n += len(STRAPS)
        return n
