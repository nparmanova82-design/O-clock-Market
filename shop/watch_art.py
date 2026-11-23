"""Soat rasmlarini SVG ko‘rinishida chizadi.

Admin haqiqiy surat yuklamaguncha har bir soat uchun rasm shu yerda hosil bo‘ladi: korpus shakli,
rangi, siferblat, tasma va uslub (g‘avvos, uchuvchi, smart, devor soati...) soat ma’lumotlaridan olinadi.
Strelkalar klassik 10:10 holatida turadi; `live=True` bo‘lsa, JS ularni hozirgi vaqtga buradi.
Rasm shaffof fonda — saytdagi yog‘och fon ustida soat stolda yotgandek ko‘rinadi.
Soyasi CSS’da (--watch-shadow) beriladi: SVG ichidagi filtr scrollni qotirardi.
"""
import math
from html import escape

from .choices import DIAL_HEX, STRAP_HEX

# Chizish kodi o‘zgarsa, shu raqamni oshiring: rasm manzili o‘zgarib, eski kesh ishlatilmaydi
ART_VERSION = 5

CX = CY = 200

METALS = {  # yorug‘, o‘rta, to‘q
    "steel": ("#f7f8f9", "#c3c8cd", "#7d848b"),
    "gold": ("#fcecb8", "#d6aa52", "#977022"),
    "rose": ("#f9ddcf", "#d39a80", "#9d634d"),
    "black": ("#626264", "#2d2d2f", "#111112"),
    "bronze": ("#edbf88", "#b47f3e", "#704a20"),
    "titanium": ("#dfdcd6", "#a5a29c", "#6d6b66"),
    "white": ("#ffffff", "#efede9", "#c8c5bf"),
    "wood": ("#d2a676", "#9b6b3f", "#61401f"),
}
BEZELS = {
    "black": ("#1b1b1c", "#1b1b1c"), "blue": ("#1c3565", "#1c3565"), "green": ("#1d4a34", "#1d4a34"),
    "red": ("#8f2420", "#8f2420"), "pepsi": ("#a5282a", "#1c3565"), "batman": ("#1c3565", "#1b1b1c"),
}
KIDS_COLORS = ["#e4572e", "#f3a712", "#29a36a", "#2d7dd2", "#a14ebf", "#e84a8a"]
ROMAN = ["XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "Helvetica, Arial, sans-serif"

# 10:10:35 — soat suratlaridagi an’anaviy holat
POSE = {"h": 305.0, "m": 60.0, "s": 210.0}


# — Rang va geometriya yordamchilari —

def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def mix(a, b, t):
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(_rgb(a), _rgb(b)))


def light(h, t=0.2):
    return mix(h, "#ffffff", t)


def dark(h, t=0.2):
    return mix(h, "#000000", t)


def lum(h):
    r, g, b = (v / 255 for v in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def n(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


def pt(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


SEGMENTS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
            "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def spec_from_watch(w):
    return {
        "style": w.style,
        "shape": w.case_shape,
        "finish": w.case_finish,
        "dial": w.dial_color,
        "strap": w.strap_material,
        "strap_color": w.strap_color,
        "bezel": w.bezel_color,
        "brand": w.brand.name,
        "mechanism": w.mechanism,
        "size": w.case_size,
        "water": w.water_resistance,
        "features": {f.slug for f in w.features.all()},
        "label": str(w),
    }


DEFAULT_SPECS = {  # soat turi bo‘sh bo‘lsa, kategoriya rasmi uchun
    "classic": dict(shape="round", finish="gold", dial="white", strap="leather", strap_color="brown"),
    "sport": dict(shape="round", finish="steel", dial="blue", strap="bracelet", strap_color="metal"),
    "diver": dict(shape="round", finish="steel", dial="black", strap="bracelet", strap_color="metal",
                  bezel="black"),
    "pilot": dict(shape="round", finish="steel", dial="black", strap="leather", strap_color="tan"),
    "chrono": dict(shape="round", finish="steel", dial="white", strap="leather", strap_color="black"),
    "luxury": dict(shape="round", finish="gold", dial="champagne", strap="bracelet", strap_color="metal"),
    "field": dict(shape="round", finish="steel", dial="black", strap="nylon", strap_color="olive"),
    "digital": dict(shape="rect", finish="black", dial="black", strap="rubber", strap_color="black"),
    "smart": dict(shape="rect", finish="black", dial="black", strap="silicone", strap_color="black"),
    "kids": dict(shape="round", finish="white", dial="white", strap="silicone", strap_color="sky"),
    "pocket": dict(shape="round", finish="gold", dial="cream", strap="chain", strap_color="metal"),
    "wall": dict(shape="round", finish="wood", dial="white", strap="none", strap_color="metal"),
    "table": dict(shape="round", finish="wood", dial="cream", strap="none", strap_color="metal"),
    "alarm": dict(shape="round", finish="steel", dial="white", strap="none", strap_color="red"),
}


def default_spec(style, label=""):
    base = dict(style=style, bezel="", brand="AEVUM", mechanism="quartz", size=40, water=50,
                features=set(), label=label)
    base.update(DEFAULT_SPECS.get(style, DEFAULT_SPECS["classic"]))
    if style == "smart":
        base["mechanism"] = "smart"
    return base


class Art:
    def __init__(self, spec, uid="w", live=False):
        self.s = spec
        self.uid = uid
        self.live = live
        self.defs = []
        self.out = []
        self.metal = METALS.get(spec["finish"], METALS["steel"])
        self.dial = DIAL_HEX.get(spec["dial"], "#161616")
        self.dark_dial = lum(self.dial) < 0.42
        self.ink = "#f3efe6" if self.dark_dial else "#1e1c1a"
        sc = spec["strap_color"]
        self.strap_c = self.metal[1] if sc == "metal" else STRAP_HEX.get(sc, "#1d1c1b")
        self.lume = "#eef1e4"
        self._base_defs()

    # — umumiy —
    def id(self, name):
        return f"{self.uid}-{name}"

    def url(self, name):
        return f"url(#{self.id(name)})"

    def add(self, *parts):
        self.out.extend(parts)

    def _grad(self, name, stops, x2=1, y2=1, x1=0, y1=0):
        s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        self.defs.append(f'<linearGradient id="{self.id(name)}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>')

    def _base_defs(self):
        lt, md, dk = self.metal
        self._grad("metal", [(0, lt), (.45, md), (1, dk)])
        self._grad("metal2", [(0, dk), (.55, md), (1, lt)])
        self._grad("metalh", [(0, dk), (.22, md), (.5, lt), (.78, md), (1, dk)], x2=1, y2=0)
        self._grad("strap", [(0, dark(self.strap_c, .28)), (.18, self.strap_c), (.5, light(self.strap_c, .07)),
                             (.82, self.strap_c), (1, dark(self.strap_c, .28))], x2=1, y2=0)
        d = self.dial
        self.defs.append(
            f'<radialGradient id="{self.id("dial")}" cx=".5" cy=".42" r=".62">'
            f'<stop offset="0" stop-color="{light(d, .14)}"/><stop offset=".62" stop-color="{d}"/>'
            f'<stop offset="1" stop-color="{dark(d, .3)}"/></radialGradient>')
        self._grad("glass", [(0, "#ffffff"), (1, "#ffffff")])
        self.defs.append(
            f'<linearGradient id="{self.id("shine")}" x1="0" y1="0" x2=".7" y2=".9">'
            f'<stop offset="0" stop-color="#fff" stop-opacity=".38"/>'
            f'<stop offset=".5" stop-color="#fff" stop-opacity="0"/></linearGradient>')

    def svg(self, size=None):
        label = escape(self.s.get("label") or self.s.get("brand", ""))
        wh = f' width="{size}" height="{size}"' if size else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400"{wh} role="img" '
                f'aria-label="{label}"><defs>{"".join(self.defs)}</defs>'
                f'<g>{"".join(self.out)}</g></svg>')

    # — strelkalar —
    def hand(self, which, shape, length, width, color, cx=CX, cy=CY, lume=False, tail=None):
        tail = width * 1.6 if tail is None else tail
        x, y = cx, cy
        if shape == "dauphine":
            body = (f'<path d="M{n(x)} {n(y - length)} L{n(x + width)} {n(y)} L{n(x)} {n(y + tail)} '
                    f'L{n(x - width)} {n(y)}Z" fill="{color}"/>'
                    f'<path d="M{n(x)} {n(y - length)} L{n(x + width)} {n(y)} L{n(x)} {n(y + tail)}Z" '
                    f'fill="{light(color, .35) if lum(color) < .5 else dark(color, .18)}"/>')
        elif shape == "sword":
            body = (f'<path d="M{n(x)} {n(y - length)} L{n(x + width / 2)} {n(y - length * .8)} '
                    f'L{n(x + width / 2)} {n(y + tail)} L{n(x - width / 2)} {n(y + tail)} '
                    f'L{n(x - width / 2)} {n(y - length * .8)}Z" fill="{color}"/>')
            if lume:
                body += (f'<path d="M{n(x)} {n(y - length * .93)} L{n(x + width * .28)} {n(y - length * .8)} '
                         f'L{n(x + width * .28)} {n(y - length * .2)} L{n(x - width * .28)} {n(y - length * .2)} '
                         f'L{n(x - width * .28)} {n(y - length * .8)}Z" fill="{self.lume}"/>')
        elif shape == "spade":
            body = (f'<rect x="{n(x - width * .22)}" y="{n(y - length)}" width="{n(width * .44)}" '
                    f'height="{n(length + tail)}" fill="{color}"/>'
                    f'<circle cx="{n(x)}" cy="{n(y - length * .72)}" r="{n(width * .62)}" fill="{color}"/>')
        else:  # baton
            body = (f'<rect x="{n(x - width / 2)}" y="{n(y - length)}" width="{n(width)}" '
                    f'height="{n(length + tail)}" rx="{n(width / 2)}" fill="{color}"/>')
            if lume:
                body += (f'<rect x="{n(x - width * .27)}" y="{n(y - length * .94)}" width="{n(width * .54)}" '
                         f'height="{n(length * .7)}" rx="{n(width * .27)}" fill="{self.lume}"/>')
        self._place(which, body, cx, cy)

    def second(self, length, color, cx=CX, cy=CY, lollipop=False):
        body = (f'<rect x="{n(cx - .9)}" y="{n(cy - length)}" width="1.8" height="{n(length * 1.25)}" '
                f'fill="{color}"/><circle cx="{n(cx)}" cy="{n(cy + length * .2)}" r="3" fill="{color}"/>')
        if lollipop:
            body += f'<circle cx="{n(cx)}" cy="{n(cy - length * .72)}" r="4" fill="{self.lume}" stroke="{color}" stroke-width="1.6"/>'
        self._place("s", body, cx, cy)

    def _place(self, which, body, cx, cy):
        rot = f'rotate({n(POSE[which])} {n(cx)} {n(cy)})'
        cls = f' class="hand-{which}" data-c="{n(cx)} {n(cy)}"' if self.live else ""
        self.add(f'<g transform="{rot}"{cls}>{body}</g>')

    def cap(self, color, cx=CX, cy=CY, r=4.5):
        self.add(f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{color}"/>'
                 f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r * .4)}" fill="{dark(color, .4)}"/>')

    def text(self, x, y, s, size, color, family=SANS, weight=500, spacing=1, anchor="middle", extra=""):
        self.add(f'<text x="{n(x)}" y="{n(y)}" font-family="{family}" font-size="{n(size)}" '
                 f'font-weight="{weight}" letter-spacing="{spacing}" fill="{color}" text-anchor="{anchor}" '
                 f'dominant-baseline="middle"{extra}>{escape(s)}</text>')

    # — qo‘l soati —
    def wrist(self):
        s = self.s
        style = s["style"]
        R = 86 + max(-10, min(12, (s["size"] - 40) * 1.5))
        shape = s["shape"]
        hw, hh = {"round": (R, R), "square": (R * .9, R * .9), "rect": (R * .72, R * 1.02),
                  "tonneau": (R * .86, R * 1.04), "octagon": (R, R)}.get(shape, (R, R))
        self.R, self.hw, self.hh = R, hw, hh

        integrated = shape == "octagon" and s["strap"] in ("bracelet", "rubber", "ceramic", "silicone")
        sw = R * (1.28 if integrated else 1.02)
        self.straps(sw, hh)
        if not integrated:
            self.lugs(sw, hh, R, shape)
        self.crown(hw, R, style)
        self.case(shape, R, hw, hh, style)
        self.dial_face(style, shape, R, hw, hh)

    def straps(self, sw, hh):
        kind = self.s["strap"]
        near = hh * .72
        for top in (True, False):
            y0 = CY - near if top else CY + near
            y1 = -8 if top else 408
            self.strap_piece(kind, y0, y1, sw, sw * .9, top)

    def strap_piece(self, kind, y0, y1, w0, w1, top, holes=True):
        def xs(y, inset=0.0):
            t = (y - y0) / (y1 - y0)
            w = w0 + (w1 - w0) * t
            return CX - w / 2 + inset, CX + w / 2 - inset

        path = (f'M{n(xs(y0)[0])} {n(y0)} L{n(xs(y0)[1])} {n(y0)} L{n(xs(y1)[1])} {n(y1)} '
                f'L{n(xs(y1)[0])} {n(y1)}Z')
        c = self.strap_c
        sign = -1 if top else 1
        if kind in ("bracelet", "ceramic"):
            step = 21
            y = y0
            fill_side = self.url("metalh") if kind == "bracelet" else self.url("strap")
            fill_mid = self.url("metal") if kind == "bracelet" else light(c, .12)
            while (y - y1) * sign < 0:
                ya, yb = y, y + sign * (step - 1.6)
                lo, hi = sorted((ya, yb))
                l, r = xs((ya + yb) / 2)
                w = r - l
                side, mid = w * .3, w * .4 - 3
                self.add(f'<rect x="{n(l)}" y="{n(lo)}" width="{n(side)}" height="{n(hi - lo)}" rx="2.5" fill="{fill_side}"/>',
                         f'<rect x="{n(l + side + 1.5)}" y="{n(lo)}" width="{n(mid)}" height="{n(hi - lo)}" rx="2" fill="{fill_mid}"/>',
                         f'<rect x="{n(r - side)}" y="{n(lo)}" width="{n(side)}" height="{n(hi - lo)}" rx="2.5" fill="{fill_side}"/>')
                y += sign * step
            return
        if kind == "mesh":
            pid = self.id("mesh")
            if not any(pid in d for d in self.defs):
                self.defs.append(f'<pattern id="{pid}" width="3" height="3" patternUnits="userSpaceOnUse">'
                                 f'<path d="M0 3L3 0" stroke="{self.metal[2]}" stroke-width=".7" opacity=".55"/></pattern>')
            self.add(f'<path d="{path}" fill="{self.url("metalh")}"/>', f'<path d="{path}" fill="url(#{pid})"/>')
            return
        self.add(f'<path d="{path}" fill="{self.url("strap")}"/>')
        stitch = light(c, .4) if lum(c) < .5 else dark(c, .3)
        if kind == "leather":
            for inset in (5.5,):
                (a0, b0), (a1, b1) = xs(y0, inset), xs(y1, inset)
                for xa, xb in ((a0, a1), (b0, b1)):
                    self.add(f'<line x1="{n(xa)}" y1="{n(y0)}" x2="{n(xb)}" y2="{n(y1)}" stroke="{stitch}" '
                             f'stroke-width="1.1" stroke-dasharray="4 3.2" opacity=".75"/>')
            if not top and holes:
                for i in range(3):
                    hy = y0 + 92 + i * 22
                    if hy < 392:
                        self.add(f'<ellipse cx="{CX}" cy="{n(hy)}" rx="3.2" ry="2.6" fill="{dark(c, .55)}"/>')
        elif kind in ("rubber", "silicone"):
            if kind == "rubber":
                for i in range(1, 4):
                    gy = y0 + sign * (10 + i * 11)
                    l, r = xs(gy, 7)
                    self.add(f'<line x1="{n(l)}" y1="{n(gy)}" x2="{n(r)}" y2="{n(gy)}" stroke="{dark(c, .35)}" '
                             f'stroke-width="2.2" stroke-linecap="round" opacity=".6"/>')
            if not top and holes:
                for i in range(5):
                    hy = y0 + 64 + i * 18
                    if hy < 396:
                        self.add(f'<circle cx="{CX}" cy="{n(hy)}" r="3.2" fill="{dark(c, .5)}"/>')
        elif kind == "nylon":
            stripe = light(c, .55) if lum(c) < .45 else dark(c, .45)
            for off in (-.2, .2):
                (a0, b0), (a1, b1) = xs(y0), xs(y1)
                w0_, w1_ = b0 - a0, b1 - a1
                xa, xb = CX + w0_ * off, CX + w1_ * off
                self.add(f'<path d="M{n(xa - 4)} {n(y0)} L{n(xa + 4)} {n(y0)} L{n(xb + 3.6)} {n(y1)} '
                         f'L{n(xb - 3.6)} {n(y1)}Z" fill="{stripe}" opacity=".85"/>')
            for i in range(2):
                gy = y0 + sign * (30 + i * 8)
                l, r = xs(gy, 8)
                self.add(f'<line x1="{n(l)}" y1="{n(gy)}" x2="{n(r)}" y2="{n(gy)}" stroke="{stitch}" '
                         f'stroke-width="1" stroke-dasharray="3 2" opacity=".7"/>')

    def lugs(self, sw, hh, R, shape):
        lw = R * .15
        reach = R * .2 if shape == "round" else R * .12
        for side in (-1, 1):
            x = CX + side * (sw / 2 + lw / 2 - 1)
            for top in (-1, 1):
                y_in = CY + top * hh * .5
                y_out = CY + top * (hh + reach)
                lo, hi = sorted((y_in, y_out))
                self.add(f'<rect x="{n(x - lw / 2)}" y="{n(lo)}" width="{n(lw)}" height="{n(hi - lo)}" '
                         f'rx="{n(lw / 2.4)}" fill="{self.url("metalh")}"/>')

    def crown(self, hw, R, style):
        cw, chh = R * .13, R * (.3 if style == "pilot" else .23)
        x = CX + hw - 4
        if style == "chrono":
            for ang in (58, 122):
                px, py = pt(CX, CY, hw + 2, ang)
                self.add(f'<rect x="{n(px - 6)}" y="{n(py - 5.5)}" width="{n(R * .14)}" height="11" rx="2.5" '
                         f'fill="{self.url("metal")}" transform="rotate({n(ang - 90)} {n(px)} {n(py)})"/>')
        if style == "diver":
            for dy in (-1, 1):
                self.add(f'<path d="M{n(x)} {n(CY + dy * chh * .95)} q{n(cw * .9)} 0 {n(cw * .7)} {n(-dy * chh * .45)}" '
                         f'fill="none" stroke="{self.metal[1]}" stroke-width="5" stroke-linecap="round"/>')
        self.add(f'<rect x="{n(x)}" y="{n(CY - chh / 2)}" width="{n(cw)}" height="{n(chh)}" rx="2.5" '
                 f'fill="{self.url("metal")}"/>')
        for i in range(1, 6):
            yy = CY - chh / 2 + i * chh / 6
            self.add(f'<line x1="{n(x + 3)}" y1="{n(yy)}" x2="{n(x + cw - 1)}" y2="{n(yy)}" '
                     f'stroke="{self.metal[2]}" stroke-width=".8" opacity=".7"/>')

    def case(self, shape, R, hw, hh, style):
        m, m2 = self.url("metal"), self.url("metal2")
        lt = self.metal[0]
        if shape == "round" or shape == "octagon":
            self.add(f'<circle cx="{CX}" cy="{CY}" r="{n(R)}" fill="{m}"/>',
                     f'<circle cx="{CX}" cy="{CY}" r="{n(R - 1.5)}" fill="none" stroke="{lt}" stroke-opacity=".55" stroke-width="1.5"/>')
        elif shape == "tonneau":
            self.add(f'<path d="{self._tonneau(hw, hh)}" fill="{m}"/>')
        else:
            self.add(f'<rect x="{n(CX - hw)}" y="{n(CY - hh)}" width="{n(hw * 2)}" height="{n(hh * 2)}" '
                     f'rx="{n(R * .2)}" fill="{m}"/>')

        # bezel
        if shape == "octagon":
            pts = " ".join(f"{n(x)},{n(y)}" for x, y in (pt(CX, CY, R * .97, 22.5 + i * 45) for i in range(8)))
            self.add(f'<polygon points="{pts}" fill="{m2}" stroke="{self.metal[2]}" stroke-width=".8"/>')
            for i in range(8):
                sx, sy = pt(CX, CY, R * .86, 22.5 + i * 45)
                self.add(f'<circle cx="{n(sx)}" cy="{n(sy)}" r="3" fill="{m}" stroke="{self.metal[2]}" stroke-width=".6"/>'
                         f'<line x1="{n(sx - 2)}" y1="{n(sy)}" x2="{n(sx + 2)}" y2="{n(sy)}" stroke="{self.metal[2]}" '
                         f'stroke-width=".8" transform="rotate({i * 45 + 20} {n(sx)} {n(sy)})"/>')
        elif shape == "round":
            if style == "diver" or (style == "sport" and self.s["bezel"]):
                self.diver_bezel(R)
            elif style == "luxury":
                self.add(f'<circle cx="{CX}" cy="{CY}" r="{n(R * .95)}" fill="{m2}"/>')
                for i in range(60):
                    a, b = pt(CX, CY, R * .95, i * 6), pt(CX, CY, R * .83, i * 6)
                    col = self.metal[0] if i % 2 else self.metal[2]
                    self.add(f'<line x1="{n(a[0])}" y1="{n(a[1])}" x2="{n(b[0])}" y2="{n(b[1])}" stroke="{col}" '
                             f'stroke-width="2.4" opacity=".75"/>')
            else:
                self.add(f'<circle cx="{CX}" cy="{CY}" r="{n(R * .91)}" fill="{m2}"/>')
        elif shape == "tonneau":
            self.add(f'<path d="{self._tonneau(hw * .88, hh * .9)}" fill="{m2}"/>')
        else:
            inset = R * .09
            self.add(f'<rect x="{n(CX - hw + inset)}" y="{n(CY - hh + inset)}" width="{n((hw - inset) * 2)}" '
                     f'height="{n((hh - inset) * 2)}" rx="{n(R * .14)}" fill="{m2}"/>')

    def _tonneau(self, hw, hh):
        top = hw * .82
        return (f'M{n(CX - top)} {n(CY - hh)} L{n(CX + top)} {n(CY - hh)} '
                f'Q{n(CX + hw * 1.12)} {n(CY)} {n(CX + top)} {n(CY + hh)} L{n(CX - top)} {n(CY + hh)} '
                f'Q{n(CX - hw * 1.12)} {n(CY)} {n(CX - top)} {n(CY - hh)}Z')

    def diver_bezel(self, R):
        c1, c2 = BEZELS.get(self.s["bezel"] or "black", BEZELS["black"])
        ro, ri = R * .96, R * .76
        self.add(f'<circle cx="{CX}" cy="{CY}" r="{n(ro + 1)}" fill="{self.url("metal2")}"/>')
        for col, a0, a1 in ((c1, -90, 90), (c2, 90, 270)):
            p0o, p1o = pt(CX, CY, ro - 2, a0), pt(CX, CY, ro - 2, a1)
            p0i, p1i = pt(CX, CY, ri, a0), pt(CX, CY, ri, a1)
            self.add(f'<path d="M{n(p0o[0])} {n(p0o[1])} A{n(ro - 2)} {n(ro - 2)} 0 0 1 {n(p1o[0])} {n(p1o[1])} '
                     f'L{n(p1i[0])} {n(p1i[1])} A{n(ri)} {n(ri)} 0 0 0 {n(p0i[0])} {n(p0i[1])}Z" fill="{col}"/>')
        mark = "#eae6dc"
        mid = (ro + ri) / 2
        for i in range(60):
            if i == 0:
                a, b, c = pt(CX, CY, ro - 4, -6), pt(CX, CY, ro - 4, 6), pt(CX, CY, ri + 4, 0)
                self.add(f'<polygon points="{n(a[0])},{n(a[1])} {n(b[0])},{n(b[1])} {n(c[0])},{n(c[1])}" fill="{mark}"/>')
                continue
            if i % 10 == 0:
                self.add(f'<text x="{CX}" y="{n(CY - mid)}" font-family="{SANS}" font-size="{n(R * .13)}" '
                         f'font-weight="700" fill="{mark}" text-anchor="middle" dominant-baseline="middle" '
                         f'transform="rotate({i * 6} {CX} {CY})">{i}</text>')
            elif i % 5 == 0 or i < 15:
                long_ = i % 5 == 0
                a = pt(CX, CY, ro - 4, i * 6)
                b = pt(CX, CY, ro - (11 if long_ else 7), i * 6)
                self.add(f'<line x1="{n(a[0])}" y1="{n(a[1])}" x2="{n(b[0])}" y2="{n(b[1])}" stroke="{mark}" '
                         f'stroke-width="{2.2 if long_ else 1.1}"/>')

    # — siferblat —
    def dial_face(self, style, shape, R, hw, hh):
        cid = self.id("clip")
        if shape in ("round", "octagon"):
            rd = R * {"diver": .74, "luxury": .81}.get(style, .84)
            if shape == "octagon":
                rd = R * .76
            if style == "sport" and self.s["bezel"]:
                rd = R * .74
            self.rd, self.dw, self.dh, self.dial_kind = rd, rd, rd, "circle"
            shape_el = f'<circle cx="{CX}" cy="{CY}" r="{n(rd)}"/>'
        else:
            inset = R * .16
            dw, dh = hw - inset, hh - inset
            self.rd, self.dw, self.dh, self.dial_kind = min(dw, dh), dw, dh, "rect"
            if shape == "tonneau":
                shape_el = f'<path d="{self._tonneau(dw, dh)}"/>'
                self.dw *= .92
            else:
                shape_el = (f'<rect x="{n(CX - dw)}" y="{n(CY - dh)}" width="{n(dw * 2)}" height="{n(dh * 2)}" '
                            f'rx="{n(R * .08)}"/>')
        self.defs.append(f'<clipPath id="{cid}">{shape_el}</clipPath>')
        self.add(f'<g clip-path="url(#{cid})"><rect x="0" y="0" width="400" height="400" fill="{self.url("dial")}"/>')
        if self.dial_kind == "circle" and style not in ("kids", "field", "pilot"):
            self.sunburst()
        if shape == "octagon":
            self.tapisserie()
        self.add('</g>')

        getattr(self, f"dial_{style}", self.dial_classic)()

        # oyna yaltirashi
        self.add(f'<g clip-path="url(#{cid})"><path d="M{n(CX - self.dw * 1.1)} {n(CY - self.dh * 1.1)} '
                 f'L{n(CX + self.dw * 1.1)} {n(CY - self.dh * 1.1)} L{n(CX - self.dw * 1.1)} {n(CY + self.dh * .35)}Z" '
                 f'fill="{self.url("shine")}"/></g>')

    def sunburst(self):
        rays = []
        for i in range(0, 360, 4):
            a, b = pt(CX, CY, 4, i), pt(CX, CY, self.rd, i)
            rays.append(f"M{n(a[0])} {n(a[1])}L{n(b[0])} {n(b[1])}")
        col = "#ffffff" if self.dark_dial else "#000000"
        self.add(f'<path d="{"".join(rays)}" stroke="{col}" stroke-width=".9" opacity=".06"/>')

    def tapisserie(self):
        step = 6
        lines = "".join(f"M{x} 0V400M0 {x}H400" for x in range(0, 401, step))
        self.add(f'<path d="{lines}" stroke="{dark(self.dial, .35)}" stroke-width="1.2" opacity=".45"/>')

    def dpt(self, deg, inset):
        if self.dial_kind == "circle":
            return pt(CX, CY, self.rd - inset, deg)
        a = math.radians(deg)
        dx, dy = math.sin(a), -math.cos(a)
        hw, hh = self.dw - inset, self.dh - inset
        t = min(hw / abs(dx) if abs(dx) > 1e-6 else 1e9, hh / abs(dy) if abs(dy) > 1e-6 else 1e9)
        return CX + dx * t, CY + dy * t

    def minute_track(self, inset=3, length=4, every=1, width=.8, color=None, skip_hours=True):
        color = color or self.ink
        d = []
        for i in range(0, 60, every):
            if skip_hours and i % 5 == 0:
                continue
            a, b = self.dpt(i * 6, inset), self.dpt(i * 6, inset + length)
            d.append(f"M{n(a[0])} {n(a[1])}L{n(b[0])} {n(b[1])}")
        self.add(f'<path d="{"".join(d)}" stroke="{color}" stroke-width="{width}" opacity=".75"/>')

    def batons(self, inset, length, width, fill, stroke=None, double12=True, skip=()):
        for h in range(12):
            if h in skip:
                continue
            ang = h * 30
            a, b = self.dpt(ang, inset), self.dpt(ang, inset + length)
            offs = (-width * .75, width * .75) if (h == 0 and double12) else (0,)
            for off in offs:
                ox, oy = math.cos(math.radians(ang)) * off, math.sin(math.radians(ang)) * off
                xy = f'x1="{n(a[0] + ox)}" y1="{n(a[1] + oy)}" x2="{n(b[0] + ox)}" y2="{n(b[1] + oy)}"'
                # Chiziqning bitta stroke’i bor: hoshiya uchun avval kengroq chiziq, ustidan asosiysi
                if stroke:
                    self.add(f'<line {xy} stroke="{stroke}" stroke-width="{n(width + 2)}" stroke-linecap="round"/>')
                self.add(f'<line {xy} stroke="{fill}" stroke-width="{n(width)}" stroke-linecap="round"/>')

    def numerals(self, labels, inset, size, color, family=SANS, weight=600, skip=(), colors=None):
        for h, lab in enumerate(labels):
            if h in skip or not lab:
                continue
            x, y = self.dpt(h * 30, inset)
            self.text(x, y + size * .04, lab, size, colors[h % len(colors)] if colors else color, family, weight, 0)

    def date_window(self, ang=90, cyclops=False):
        rd = self.rd
        x, y = self.dpt(ang, rd * .3)
        w, h = rd * .21, rd * .15
        self.add(f'<rect x="{n(x - w / 2)}" y="{n(y - h / 2)}" width="{n(w)}" height="{n(h)}" rx="1.5" '
                 f'fill="#faf8f3" stroke="{dark(self.metal[1], .2)}" stroke-width="1"/>')
        self.text(x, y + .5, "18", h * .72, "#1e1c1a", SANS, 600, 0)
        if cyclops:
            self.add(f'<rect x="{n(x - w * .75)}" y="{n(y - h * .8)}" width="{n(w * 1.5)}" height="{n(h * 1.6)}" '
                     f'rx="4" fill="#ffffff" opacity=".18" stroke="#fff" stroke-opacity=".5" stroke-width=".8"/>')

    def brand_text(self, family=SANS, sub=None, y_brand=.4, y_sub=.42):
        rd = self.rd
        self.text(CX, CY - rd * y_brand, self.s["brand"].upper(), rd * .105, self.ink, family, 600, 1.6)
        if sub:
            self.text(CX, CY + rd * y_sub, sub, rd * .065, self.ink, SANS, 500, 1.2,
                      extra=' opacity=".75"')

    def subtitle(self):
        mech = self.s["mechanism"]
        return {"automatic": "AUTOMATIC", "mechanical": "HAND WOUND", "solar": "SOLAR",
                "kinetic": "KINETIC"}.get(mech)

    # uslublar
    def dial_classic(self):
        rd = self.rd
        roman = not self.dark_dial or self.dial_kind == "rect"
        hand_c = ("#1d3a7c" if roman and not self.dark_dial else
                  (self.metal[0] if self.dark_dial else "#1e1c1a"))
        if roman:
            self.minute_track(2, 4, skip_hours=False, width=.7)
            self.numerals(ROMAN, rd * .2, rd * .15, self.ink, SERIF, 500)
        else:
            self.minute_track(3, 3)
            self.batons(rd * .08, rd * .16, 2.4, self.metal[0], double12=True)
        small_seconds = self.s["mechanism"] == "mechanical" and self.dial_kind == "circle"
        self.brand_text(SERIF, None if small_seconds else self.subtitle(), y_sub=.36)
        if small_seconds:
            sx, sy, sr = CX, CY + rd * .46, rd * .2
            self.add(f'<circle cx="{n(sx)}" cy="{n(sy)}" r="{n(sr)}" fill="none" stroke="{self.ink}" '
                     f'stroke-width=".7" opacity=".7"/>')
            for i in range(12):
                a, b = pt(sx, sy, sr, i * 30), pt(sx, sy, sr - 3, i * 30)
                self.add(f'<line x1="{n(a[0])}" y1="{n(a[1])}" x2="{n(b[0])}" y2="{n(b[1])}" stroke="{self.ink}" stroke-width=".7"/>')
            self.add(f'<line x1="{n(sx)}" y1="{n(sy)}" x2="{n(pt(sx, sy, sr * .85, 210)[0])}" '
                     f'y2="{n(pt(sx, sy, sr * .85, 210)[1])}" stroke="{hand_c}" stroke-width="1.2"/>')
        if "sana" in self.s["features"] and not small_seconds:
            self.date_window()
        self.hand("h", "dauphine", rd * .52, rd * .055, hand_c)
        self.hand("m", "dauphine", rd * .8, rd * .045, hand_c)
        if not small_seconds:
            self.second(rd * .86, hand_c)
        self.cap(hand_c)

    def dial_luxury(self):
        rd = self.rd
        self.minute_track(3, 4, color=self.ink)
        self.batons(rd * .1, rd * .2, 4.2, self.metal[1], stroke=None, skip=(3,))
        self.batons(rd * .1, rd * .2, 1.4, self.metal[0], skip=(3,))
        self.brand_text(SERIF, self.subtitle() or "SUPERLATIVE", y_brand=.38, y_sub=.38)
        self.date_window(cyclops=True)
        self.hand("h", "baton", rd * .5, 6, self.metal[1], lume=True)
        self.hand("m", "baton", rd * .78, 4.6, self.metal[1], lume=True)
        self.second(rd * .86, self.metal[1])
        self.cap(self.metal[1])

    def dial_sport(self):
        rd = self.rd
        self.minute_track(3, 4)
        self.batons(rd * .08, rd * .2, 5, self.lume, stroke=self.ink, skip=(3,) if "sana" in self.s["features"] else ())
        self.brand_text(SANS, self.subtitle() or f"{self.s['water']} M")
        if "sana" in self.s["features"]:
            self.date_window()
        hc = self.metal[0] if self.dark_dial else "#26292c"
        self.hand("h", "baton", rd * .52, 7, hc, lume=True)
        self.hand("m", "baton", rd * .8, 5.4, hc, lume=True)
        self.second(rd * .88, "#d9532b")
        self.cap("#d9532b")

    def dial_diver(self):
        rd = self.rd
        self.minute_track(2, 4)
        for h in range(12):
            if h == 3 and "sana" in self.s["features"]:
                continue
            x, y = self.dpt(h * 30, rd * .17)
            if h == 0:
                a, b, c = self.dpt(-7, rd * .07), self.dpt(7, rd * .07), self.dpt(0, rd * .3)
                self.add(f'<polygon points="{n(a[0])},{n(a[1])} {n(b[0])},{n(b[1])} {n(c[0])},{n(c[1])}" '
                         f'fill="{self.lume}" stroke="{self.metal[1]}" stroke-width="1"/>')
            elif h in (3, 6, 9):
                a, b = self.dpt(h * 30, rd * .07), self.dpt(h * 30, rd * .3)
                self.add(f'<line x1="{n(a[0])}" y1="{n(a[1])}" x2="{n(b[0])}" y2="{n(b[1])}" stroke="{self.metal[1]}" '
                         f'stroke-width="9" stroke-linecap="round"/><line x1="{n(a[0])}" y1="{n(a[1])}" '
                         f'x2="{n(b[0])}" y2="{n(b[1])}" stroke="{self.lume}" stroke-width="6.4" stroke-linecap="round"/>')
            else:
                self.add(f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(rd * .075)}" fill="{self.lume}" '
                         f'stroke="{self.metal[1]}" stroke-width="1.2"/>')
        self.brand_text(SANS, f"{self.s['water']} M · DIVER", y_sub=.4)
        if "sana" in self.s["features"]:
            self.date_window()
        hc = self.metal[0]
        self.hand("h", "sword", rd * .5, 11, hc, lume=True)
        self.hand("m", "sword", rd * .78, 8.5, hc, lume=True)
        self.second(rd * .86, "#e2673a", lollipop=True)
        self.cap(hc)

    def dial_pilot(self):
        rd = self.rd
        self.minute_track(2, 5, skip_hours=False, width=1)
        labels = [""] + [str(i) for i in range(1, 12)]
        self.numerals(labels, rd * .24, rd * .2, self.ink, SANS, 700)
        a, b, c = self.dpt(-8, rd * .1), self.dpt(8, rd * .1), self.dpt(0, rd * .32)
        self.add(f'<polygon points="{n(a[0])},{n(a[1])} {n(b[0])},{n(b[1])} {n(c[0])},{n(c[1])}" fill="{self.ink}"/>')
        for off in (-13, 13):
            x, y = self.dpt(off, rd * .1)
            self.add(f'<circle cx="{n(x)}" cy="{n(y)}" r="2.4" fill="{self.ink}"/>')
        self.text(CX, CY - rd * .3, self.s["brand"].upper(), rd * .08, self.ink, SANS, 600, 1.4,
                  extra=' opacity=".7"')
        hc = self.ink
        self.hand("h", "sword", rd * .5, 10, hc, lume=True)
        self.hand("m", "sword", rd * .82, 7.5, hc, lume=True)
        self.second(rd * .88, hc)
        self.cap(hc)

    def dial_field(self):
        rd = self.rd
        self.minute_track(2, 3, skip_hours=False, width=.8)
        labels = ["12"] + [str(i) for i in range(1, 12)]
        self.numerals(labels, rd * .2, rd * .17, self.ink, SANS, 700)
        inner = [str(i) for i in (24, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23)]
        self.numerals(inner, rd * .42, rd * .075, self.ink, SANS, 500)
        self.brand_text(SANS, None, y_brand=.25)
        hc = self.metal[0] if self.dark_dial else "#26292c"
        self.hand("h", "sword", rd * .48, 9, hc, lume=True)
        self.hand("m", "sword", rd * .78, 7, hc, lume=True)
        self.second(rd * .86, "#c8a24a")
        self.cap(hc)

    def dial_chrono(self):
        rd = self.rd
        self.minute_track(2, 4)
        three = self.s["size"] >= 42
        subs = [(270, rd * .45), (90, rd * .45)] + ([(180, rd * .45)] if three else [])
        skip = {3, 9} | ({6} if three else set())
        self.batons(rd * .08, rd * .17, 3.4, self.ink if not self.dark_dial else self.metal[0], skip=skip)
        sub_fill = dark(self.dial, .25) if self.dark_dial else dark(self.dial, .06)
        for ang, dist in subs:
            sx, sy = pt(CX, CY, dist, ang)
            sr = rd * .21
            self.add(f'<circle cx="{n(sx)}" cy="{n(sy)}" r="{n(sr)}" fill="{sub_fill}" stroke="{self.ink}" '
                     f'stroke-width=".8" opacity=".95"/>')
            for i in range(12):
                a, b = pt(sx, sy, sr, i * 30), pt(sx, sy, sr - (4 if i % 3 == 0 else 2.2), i * 30)
                self.add(f'<line x1="{n(a[0])}" y1="{n(a[1])}" x2="{n(b[0])}" y2="{n(b[1])}" stroke="{self.ink}" stroke-width=".8"/>')
            tip = pt(sx, sy, sr * .85, 120 + ang)
            self.add(f'<line x1="{n(sx)}" y1="{n(sy)}" x2="{n(tip[0])}" y2="{n(tip[1])}" stroke="{self.ink}" '
                     f'stroke-width="1.4"/><circle cx="{n(sx)}" cy="{n(sy)}" r="1.8" fill="{self.ink}"/>')
        self.brand_text(SANS, "CHRONOGRAPH", y_brand=.62 if three else .4, y_sub=.72 if three else .4)
        hc = self.metal[0] if self.dark_dial else "#26292c"
        self.hand("h", "baton", rd * .5, 6, hc, lume=True)
        self.hand("m", "baton", rd * .8, 4.6, hc, lume=True)
        self.second(rd * .9, "#c8372d")
        self.cap("#c8372d")

    def dial_kids(self):
        rd = self.rd
        self.minute_track(3, 3, color="#9a9590")
        labels = ["12"] + [str(i) for i in range(1, 12)]
        self.numerals(labels, rd * .2, rd * .19, None, SANS, 800, colors=KIDS_COLORS)
        self.hand("h", "baton", rd * .46, 9, "#2b2b2b")
        self.hand("m", "baton", rd * .72, 7, "#2b2b2b")
        self.second(rd * .8, "#e4572e")
        self.cap("#e4572e", r=6)

    # — elektron va smart soatlar —
    def digital(self):
        s = self.s
        R = 90
        octagon = s["shape"] == "octagon"
        hw, hh = (R * .98, R * .98) if octagon else (R * .92, R * .84)
        self.straps(R * 1.04, hh * .9)
        body_c = self.strap_c if s["strap_color"] != "metal" else self.metal[1]
        self._grad("resin", [(0, light(body_c, .16)), (.5, body_c), (1, dark(body_c, .35))])
        for side in (-1, 1):
            for dy in (-.45, .45):
                self.add(f'<rect x="{n(CX + side * hw - (8 if side > 0 else 4))}" y="{n(CY + dy * hh - 7)}" '
                         f'width="12" height="14" rx="3" fill="{self.url("metal")}"/>')
        if octagon:
            pts = " ".join(f"{n(x)},{n(y)}" for x, y in (pt(CX, CY, R * 1.06, 22.5 + i * 45) for i in range(8)))
            self.add(f'<polygon points="{pts}" fill="{self.url("resin")}" stroke-linejoin="round" '
                     f'stroke="{self.url("resin")}" stroke-width="14"/>')
        else:
            self.add(f'<rect x="{n(CX - hw)}" y="{n(CY - hh)}" width="{n(hw * 2)}" height="{n(hh * 2)}" '
                     f'rx="{n(R * .26)}" fill="{self.url("resin")}"/>')
        plate_w, plate_h = hw * .8, hh * .74
        plate = self.url("metal") if s["case_material_hint"] == "metal" else dark(body_c, .45)
        self.add(f'<rect x="{n(CX - plate_w)}" y="{n(CY - plate_h)}" width="{n(plate_w * 2)}" height="{n(plate_h * 2)}" '
                 f'rx="10" fill="{plate}"/>')
        label_c = "#e9e4d8"
        self.text(CX, CY - plate_h + 11, s["brand"].upper(), 10.5, label_c, SANS, 700, 1.6)
        self.text(CX, CY + plate_h - 10, f"WATER RESIST · {s['water']}M", 6.5, label_c, SANS, 600, 1.2,
                  extra=' opacity=".8"')
        lw, lh = plate_w * .86, plate_h * .62
        lcd = "#c3cbb6"
        self.add(f'<rect x="{n(CX - lw)}" y="{n(CY - lh)}" width="{n(lw * 2)}" height="{n(lh * 2)}" rx="5" '
                 f'fill="{lcd}" stroke="{dark(body_c, .6)}" stroke-width="2"/>')
        self.text(CX - lw + 8, CY - lh + 9, "PA 13", 8, "#2b3027", SANS, 700, .6, anchor="start")
        self.seven_seg("1010", CX - lw + 9, CY - lh * .35, lw * 1.26, lh * 1.02, "#262b23")
        self.seven_seg("35", CX + lw * .5, CY - lh * .02, lw * .4, lh * .6, "#262b23")

    def seven_seg(self, digits, x, y, total_w, h, color):
        count = len(digits)
        gap = total_w * .08
        colon = count == 4
        w = (total_w - gap * (count - 1) - (gap * 1.2 if colon else 0)) / count
        t = max(2.2, w * .2)
        parts = []
        cx = x
        for i, ch in enumerate(digits):
            parts.append(self._digit(cx, y, w, h, t, "8", color, .08))
            parts.append(self._digit(cx, y, w, h, t, ch, color, 1))
            cx += w + gap
            if colon and i == 1:
                for yy in (y + h * .3, y + h * .7):
                    parts.append(f'<rect x="{n(cx - gap * .2)}" y="{n(yy - t / 2)}" width="{n(t)}" height="{n(t)}" fill="{color}"/>')
                cx += gap * 1.2
        self.add(f'<g transform="skewX(-6) translate({n(y * math.tan(math.radians(6)))} 0)">{"".join(parts)}</g>')

    @staticmethod
    def _digit(x, y, w, h, t, ch, color, opacity):
        g = t * .18
        segs = {
            "a": (x + t * .5 + g, y, w - t - 2 * g, t), "g": (x + t * .5 + g, y + h / 2 - t / 2, w - t - 2 * g, t),
            "d": (x + t * .5 + g, y + h - t, w - t - 2 * g, t),
            "f": (x, y + t * .5 + g, t, h / 2 - t - g), "b": (x + w - t, y + t * .5 + g, t, h / 2 - t - g),
            "e": (x, y + h / 2 + t * .5, t, h / 2 - t - g), "c": (x + w - t, y + h / 2 + t * .5, t, h / 2 - t - g),
        }
        return "".join(f'<rect x="{n(sx)}" y="{n(sy)}" width="{n(sw)}" height="{n(sh)}" rx="{n(t * .45)}" '
                       f'fill="{color}" opacity="{opacity}"/>' for sx, sy, sw, sh in (segs[k] for k in SEGMENTS[ch]))

    def smart(self):
        s = self.s
        rect = s["shape"] != "round"
        kids = s["style"] == "kids"
        R = 84
        hw, hh = (R * .8, R * .98) if rect else (R, R)
        self.straps(R * (.98 if rect else 1.0), hh * .9 if rect else hh * .75)
        if not rect:
            self.lugs(R * 1.0, R, R, "round")
        side_x = CX + hw - 4
        self.add(f'<rect x="{n(side_x)}" y="{n(CY - hh * .42)}" width="11" height="{n(R * .24)}" rx="4" '
                 f'fill="{self.url("metal")}"/>',
                 f'<rect x="{n(side_x)}" y="{n(CY + hh * .05)}" width="7" height="{n(R * .3)}" rx="3" '
                 f'fill="{self.url("metal")}"/>')
        accent = self.strap_c if s["strap_color"] not in ("metal", "black", "grey", "white") else "#7fd1ae"
        if kids:
            accent = "#ffd166"
        screen = "#050506"
        if rect:
            self.add(f'<rect x="{n(CX - hw)}" y="{n(CY - hh)}" width="{n(hw * 2)}" height="{n(hh * 2)}" '
                     f'rx="{n(R * .34)}" fill="{self.url("metal")}"/>',
                     f'<rect x="{n(CX - hw + 5)}" y="{n(CY - hh + 5)}" width="{n(hw * 2 - 10)}" height="{n(hh * 2 - 10)}" '
                     f'rx="{n(R * .29)}" fill="{screen}"/>')
            top = CY - hh + 5
            self.text(CX - hw + 22, top + 20, "PAY 13", 10, accent, SANS, 700, .8, anchor="start")
            self.text(CX + hw - 22, top + 20, "◔ 86%", 9, "#8f8f94", SANS, 600, .4, anchor="end")
            self.text(CX, CY + 4, "10:09", R * .5, "#f5f5f7", SANS, 600, -1)
            bar_y = CY + hh * .5
            for i, (lab, frac, col) in enumerate((("Qadam", .72, accent), ("Kkal", .5, "#ff8a5c"))):
                y = bar_y + i * 15
                self.text(CX - hw + 20, y, lab, 7.5, "#a3a3a8", SANS, 500, .3, anchor="start")
                self.add(f'<rect x="{n(CX - hw + 50)}" y="{n(y - 2.5)}" width="{n(hw * 2 - 72)}" height="5" rx="2.5" fill="#26262a"/>'
                         f'<rect x="{n(CX - hw + 50)}" y="{n(y - 2.5)}" width="{n((hw * 2 - 72) * frac)}" height="5" rx="2.5" fill="{col}"/>')
            self.text(CX, CY - hh * .42, "♥ 72", 10, "#ff6b6b", SANS, 600, .5)
        else:
            self.add(f'<circle cx="{CX}" cy="{CY}" r="{n(R)}" fill="{self.url("metal")}"/>',
                     f'<circle cx="{CX}" cy="{CY}" r="{n(R * .93)}" fill="#18181a"/>')
            for i in range(0, 360, 30):
                a, b = pt(CX, CY, R * .93, i), pt(CX, CY, R * .86, i)
                self.add(f'<line x1="{n(a[0])}" y1="{n(a[1])}" x2="{n(b[0])}" y2="{n(b[1])}" stroke="#77777c" stroke-width="1.4"/>')
            self.add(f'<circle cx="{CX}" cy="{CY}" r="{n(R * .84)}" fill="{screen}"/>')
            r = R * .76
            for col, frac, rr in ((accent, .7, r), ("#ff8a5c", .45, r - 7)):
                a0, a1 = pt(CX, CY, rr, -130), pt(CX, CY, rr, -130 + 260 * frac)
                large = 1 if 260 * frac > 180 else 0
                self.add(f'<path d="M{n(a0[0])} {n(a0[1])} A{n(rr)} {n(rr)} 0 {large} 1 {n(a1[0])} {n(a1[1])}" '
                         f'fill="none" stroke="{col}" stroke-width="4.5" stroke-linecap="round"/>')
            self.text(CX, CY - R * .28, "PAY 13", 10, accent, SANS, 700, .8)
            self.text(CX, CY + 6, "10:09", R * .42, "#f5f5f7", SANS, 600, -.5)
            self.text(CX, CY + R * .42, "♥ 72", 10, "#ff6b6b", SANS, 600, .5)
        self.add(f'<path d="M{n(CX - hw * .7)} {n(CY - hh * .95)} L{n(CX + hw * .2)} {n(CY - hh * .95)} '
                 f'L{n(CX - hw * .7)} {n(CY - hh * .1)}Z" fill="#fff" opacity=".06"/>')

    # — cho‘ntak, devor, stol soatlari va budilnik —
    def round_clock(self, cx, cy, rd, numerals="roman", hand_c=None, brand=True, sub=None, second=True):
        """Ichki siferblat: cho‘ntak, devor, stol soati va budilnik uchun umumiy."""
        self.rd, self.dw, self.dh, self.dial_kind = rd, rd, rd, "circle"
        self.add(f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(rd)}" fill="{self.url("dial")}"/>')
        ink = self.ink
        d = []
        for i in range(60):
            a = pt(cx, cy, rd - 3, i * 6)
            b = pt(cx, cy, rd - (9 if i % 5 == 0 else 6), i * 6)
            d.append(f"M{n(a[0])} {n(a[1])}L{n(b[0])} {n(b[1])}")
        self.add(f'<path d="{"".join(d)}" stroke="{ink}" stroke-width="1" opacity=".8"/>')
        if numerals == "roman":
            labels, fam, size, wt = ROMAN, SERIF, rd * .16, 500
        elif numerals == "arabic":
            labels, fam, size, wt = ["12"] + [str(i) for i in range(1, 12)], SANS, rd * .17, 600
        else:
            labels, fam, size, wt = [], SANS, 0, 0
            for h in range(12):
                a, b = pt(cx, cy, rd * .9, h * 30), pt(cx, cy, rd * (.7 if h % 3 == 0 else .78), h * 30)
                self.add(f'<line x1="{n(a[0])}" y1="{n(a[1])}" x2="{n(b[0])}" y2="{n(b[1])}" stroke="{ink}" '
                         f'stroke-width="{rd * .045:.1f}" stroke-linecap="round"/>')
        for h, lab in enumerate(labels):
            x, y = pt(cx, cy, rd * .76, h * 30)
            self.text(x, y + size * .04, lab, size, ink, fam, wt, 0)
        if brand:
            self.text(cx, cy - rd * .38, self.s["brand"].upper(), rd * .085, ink, SERIF if numerals == "roman" else SANS, 600, 1.5)
        if sub:
            self.text(cx, cy + rd * .4, sub, rd * .06, ink, SANS, 500, 1.2, extra=' opacity=".7"')
        hand_c = hand_c or ("#1d3a7c" if not self.dark_dial and numerals == "roman" else ink)
        shape = "spade" if numerals == "roman" else "baton"
        self.hand("h", shape, rd * .5, rd * (.09 if shape == "spade" else .05), hand_c, cx, cy)
        self.hand("m", shape, rd * .76, rd * (.07 if shape == "spade" else .036), hand_c, cx, cy)
        if second:
            self.second(rd * .84, "#c0392b", cx, cy)
        self.cap(hand_c, cx, cy, rd * .045)
        self.add(f'<path d="M{n(cx - rd)} {n(cy - rd)} L{n(cx + rd * .9)} {n(cy - rd)} L{n(cx - rd)} {n(cy + rd * .2)}Z" '
                 f'fill="{self.url("shine")}" clip-path="url(#{self.id("rc")})"/>')
        self.defs.append(f'<clipPath id="{self.id("rc")}"><circle cx="{n(cx)}" cy="{n(cy)}" r="{n(rd)}"/></clipPath>')

    def pocket(self):
        cx, cy, R = 200, 226, 118
        lt, md, dk = self.metal
        p0, p1, p2 = (200, cy - R - 34), (340, cy - R - 60), (412, 150)
        for i in range(19):
            t = i / 18
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
            dx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
            dy = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
            ang = math.degrees(math.atan2(dy, dx))
            ry = 4.6 if i % 2 else 2.2
            self.add(f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="8" ry="{ry}" fill="none" stroke="{md}" stroke-width="2.6" '
                     f'transform="rotate({n(ang)} {n(x)} {n(y)})"/>')
        self.add(f'<circle cx="200" cy="{n(cy - R - 28)}" r="15" fill="none" stroke="{self.url("metal")}" stroke-width="6"/>',
                 f'<rect x="190" y="{n(cy - R - 18)}" width="20" height="22" rx="4" fill="{self.url("metal")}"/>')
        for i in range(1, 5):
            self.add(f'<line x1="{190 + i * 4}" y1="{n(cy - R - 16)}" x2="{190 + i * 4}" y2="{n(cy - R + 2)}" '
                     f'stroke="{dk}" stroke-width=".8"/>')
        self.add(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{self.url("metal")}"/>',
                 f'<circle cx="{cx}" cy="{cy}" r="{n(R * .94)}" fill="{self.url("metal2")}"/>',
                 f'<circle cx="{cx}" cy="{cy}" r="{n(R * .9)}" fill="none" stroke="{lt}" stroke-width="1" opacity=".6"/>')
        rd = R * .86
        self.round_clock(cx, cy, rd, "roman", second=False)
        sx, sy, sr = cx, cy + rd * .46, rd * .18
        self.add(f'<circle cx="{n(sx)}" cy="{n(sy)}" r="{n(sr)}" fill="none" stroke="{self.ink}" stroke-width=".7"/>')
        tip = pt(sx, sy, sr * .85, 200)
        self.add(f'<line x1="{n(sx)}" y1="{n(sy)}" x2="{n(tip[0])}" y2="{n(tip[1])}" stroke="#1d3a7c" stroke-width="1.2"/>')

    def wall(self):
        cx = cy = 200
        R = 182
        if self.s["finish"] == "wood" or self.s["strap_color"] == "metal":
            frame = self.url("metal")
        else:
            c = self.strap_c
            self._grad("frame", [(0, light(c, .18)), (.5, c), (1, dark(c, .3))])
            frame = self.url("frame")
        self.add(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{frame}"/>',
                 f'<circle cx="{cx}" cy="{cy}" r="{n(R * .9)}" fill="{dark(self.dial, .25)}"/>')
        if self.s["finish"] == "wood":
            rings = "".join(f'<circle cx="{cx}" cy="{cy}" r="{n(R * (.91 + i * .018))}" fill="none" '
                            f'stroke="{dark(self.metal[1], .25)}" stroke-width=".6" opacity=".45"/>' for i in range(5))
            self.add(rings)
        dial = self.s["dial"]
        style = "arabic" if dial in ("white", "cream", "silver") else "bars"
        self.round_clock(cx, cy, R * .88, style, sub="QUARTZ · SILENT")

    def table(self):
        if self.s["finish"] == "wood" or self.s["strap_color"] == "metal":
            body = self.url("metal")
            base = self.metal[2]
        else:
            c = self.strap_c
            self._grad("body", [(0, light(c, .18)), (.5, c), (1, dark(c, .3))])
            body = self.url("body")
            base = dark(c, .35)
        self.add(f'<rect x="74" y="338" width="252" height="24" rx="5" fill="{base}"/>',
                 f'<rect x="96" y="360" width="28" height="10" rx="3" fill="{dark(base, .3)}"/>',
                 f'<rect x="276" y="360" width="28" height="10" rx="3" fill="{dark(base, .3)}"/>',
                 f'<path d="M90 342 L90 176 A110 110 0 0 1 310 176 L310 342Z" fill="{body}"/>')
        self._grad("ring", [(0, "#fcecb8"), (.5, "#d6aa52"), (1, "#977022")])
        self.add(f'<circle cx="200" cy="182" r="92" fill="{self.url("ring")}"/>')
        self.round_clock(200, 182, 82, "roman" if self.s["dial"] in ("cream", "white", "champagne") else "arabic")
        self.text(200, 305, self.s["brand"].upper(), 11, "#f4ead6" if lum(self.strap_c) < .5 else "#3b2a1a",
                  SERIF, 600, 3, extra=' opacity=".8"')

    def alarm(self):
        cx, cy, R = 200, 228, 112
        lt, md, dk = self.metal
        for side in (-1, 1):
            self.add(f'<line x1="{n(cx + side * 58)}" y1="{n(cy + R - 18)}" x2="{n(cx + side * 88)}" y2="{n(cy + R + 36)}" '
                     f'stroke="{md}" stroke-width="10" stroke-linecap="round"/>')
            bx, by = pt(cx, cy, R + 6, side * 38)
            self.add(f'<circle cx="{n(bx)}" cy="{n(by)}" r="44" fill="{self.url("metal")}"/>',
                     f'<circle cx="{n(bx - 10)}" cy="{n(by - 14)}" r="10" fill="#fff" opacity=".3"/>')
            kx, ky = pt(cx, cy, R + 52, side * 38)
            self.add(f'<circle cx="{n(kx)}" cy="{n(ky)}" r="6" fill="{dk}"/>')
        self.add(f'<rect x="{cx - 4}" y="{cy - R - 46}" width="8" height="40" rx="3" fill="{dk}"/>',
                 f'<rect x="{cx - 16}" y="{cy - R - 50}" width="32" height="9" rx="4" fill="{md}"/>')
        c = self.strap_c
        self._grad("body", [(0, light(c, .25)), (.45, c), (1, dark(c, .35))])
        self.add(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{self.url("body")}"/>',
                 f'<circle cx="{cx}" cy="{cy}" r="{n(R * .9)}" fill="{self.url("metal2")}"/>')
        self.round_clock(cx, cy, R * .84, "arabic", sub="ALARM")
        self.add(f'<g transform="rotate(215 {cx} {cy})"><path d="M{cx} {n(cy - R * .55)} l5 12 h-10z" fill="#c8a24a"/>'
                 f'<rect x="{cx - 1}" y="{n(cy - R * .5)}" width="2" height="{n(R * .5)}" fill="#c8a24a"/></g>')


class StrapArt(Art):
    """Alohida tasma: ikki bo‘lak, o‘rtada shpilkalar (yoki Apple ulagichlari), uchida to‘qa yoki qulf."""

    def draw(self, width_mm, fit, buckle):
        kind = self.s["strap"]
        w = 40 + width_mm * 3
        taper = .86
        top0, top1 = CY - 14, 52
        bot0, bot1 = CY + 14, 366
        metal = kind in ("bracelet", "mesh")
        lt, md, dk = self.metal

        self.strap_piece(kind, top0, top1, w, w * taper, True, holes=False)
        self.strap_piece(kind, bot0, bot1, w, w * taper, False, holes=False)
        if not metal:
            fill = self.url("strap")
            wt = w * taper
            self.add(f'<path d="M{n(CX - wt / 2)} {top1} Q{n(CX - wt / 2)} {top1 - 18} {CX} {top1 - 20} '
                     f'Q{n(CX + wt / 2)} {top1 - 18} {n(CX + wt / 2)} {top1}Z" fill="{fill}"/>',
                     f'<path d="M{n(CX - wt / 2)} {bot1} Q{n(CX - wt / 2)} {bot1 + 22} {CX} {bot1 + 26} '
                     f'Q{n(CX + wt / 2)} {bot1 + 22} {n(CX + wt / 2)} {bot1}Z" fill="{fill}"/>')
            if buckle == "pin":
                hole = dark(self.strap_c, .55)
                for i in range(6):
                    hy = bot0 + 72 + i * 17
                    if hy < bot1 - 6:
                        self.add(f'<ellipse cx="{CX}" cy="{n(hy)}" rx="3.4" ry="2.8" fill="{hole}"/>')

        # Soat tomondagi uchlar
        for y in (top0, bot0):
            if fit.startswith("apple"):
                yy = y - 12 if y == top0 else y
                self.add(f'<rect x="{n(CX - w / 2 - 3)}" y="{n(yy)}" width="{n(w + 6)}" height="12" rx="3" '
                         f'fill="{self.url("metalh")}"/>',
                         f'<line x1="{n(CX - w / 2 + 6)}" y1="{n(yy + 6)}" x2="{n(CX + w / 2 - 6)}" y2="{n(yy + 6)}" '
                         f'stroke="{dk}" stroke-width="1.2" opacity=".6"/>')
            else:
                yy = y - 6 if y == top0 else y + 2
                self.add(f'<rect x="{n(CX - w / 2 - 6)}" y="{n(yy)}" width="{n(w + 12)}" height="4" rx="2" '
                         f'fill="{self.url("metalh")}"/>')
                if fit == "quick":
                    self.add(f'<rect x="{n(CX + w * .18)}" y="{n(yy - 3)}" width="7" height="10" rx="2" fill="{md}" '
                             f'stroke="{dk}" stroke-width=".6"/>')

        # To‘qa va qulflar
        wt = w * taper
        if buckle == "pin" and not metal:
            self.add(f'<rect x="{n(CX - wt / 2 - 7)}" y="{top1 - 8}" width="{n(wt + 14)}" height="30" rx="7" fill="none" '
                     f'stroke="{self.url("metalh")}" stroke-width="5"/>',
                     f'<line x1="{CX}" y1="{top1 + 22}" x2="{CX}" y2="{top1 - 6}" stroke="{md}" stroke-width="3.2" '
                     f'stroke-linecap="round"/>',
                     f'<rect x="{n(CX - wt / 2 - 2)}" y="{top1 + 40}" width="{n(wt + 4)}" height="12" rx="3" '
                     f'fill="{dark(self.strap_c, .12)}"/>')
        elif buckle in ("deployant", "fold"):
            y = bot1 - 92 if not metal else bot0 + 74
            self.add(f'<rect x="{n(CX - wt / 2 - 2)}" y="{n(y)}" width="{n(wt + 4)}" height="58" rx="7" '
                     f'fill="{self.url("metal")}" stroke="{dk}" stroke-width=".8"/>',
                     f'<line x1="{n(CX - wt / 2 + 6)}" y1="{n(y + 29)}" x2="{n(CX + wt / 2 - 6)}" y2="{n(y + 29)}" '
                     f'stroke="{dk}" stroke-width="1.2" opacity=".55"/>')
            for side in (-1, 1):
                self.add(f'<rect x="{n(CX + side * (wt / 2 + 1) - 3)}" y="{n(y + 22)}" width="6" height="14" rx="2" '
                         f'fill="{md}" stroke="{dk}" stroke-width=".6"/>')
        elif buckle == "magnet":
            self.add(f'<rect x="{n(CX - wt / 2 - 1)}" y="{bot1 - 22}" width="{n(wt + 2)}" height="24" rx="6" '
                     f'fill="{dark(md, .45)}"/>',
                     f'<rect x="{n(CX - wt / 2 + 4)}" y="{bot1 - 18}" width="{n(wt - 8)}" height="5" rx="2.5" '
                     f'fill="#fff" opacity=".18"/>')
        if buckle == "loop" and kind == "nylon":
            self.add(f'<rect x="{n(CX - wt / 2 - 2)}" y="{top1 + 24}" width="{n(wt + 4)}" height="10" rx="3" '
                     f'fill="{dark(self.strap_c, .18)}"/>')


def render_strap(strap, uid="s", size=None):
    width = strap.width or (22 if strap.fit == "apple_l" else 20)
    spec = default_spec("classic", label=str(strap))
    spec.update(strap=strap.material, finish=strap.finish,
                strap_color="metal" if strap.color == "metal" else strap.color)
    art = StrapArt(spec, uid=uid)
    art.draw(width, strap.fit, strap.buckle)
    return art.svg(size)


def render(spec, uid="w", live=False, size=None):
    spec = dict(spec)
    spec.setdefault("case_material_hint", "")
    art = Art(spec, uid=uid, live=live)
    style = spec["style"]
    if spec.get("mechanism") == "smart":
        art.smart()
    elif style in ("pocket", "wall", "table", "alarm", "digital"):
        getattr(art, style)()
    else:
        art.wrist()
    return art.svg(size)


def render_watch(watch, uid="w", live=False, size=None):
    spec = spec_from_watch(watch)
    spec["case_material_hint"] = "metal" if watch.case_material in ("steel", "titanium", "gold") else ""
    return render(spec, uid=uid, live=live, size=size)
