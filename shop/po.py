"""Tarjima fayllari (.po/.mo) bilan ishlash — GNU gettext o‘rnatilmagan kompyuterda ham (Windows, Render).

make_translations buyrug‘i matnlarni yig‘adi va .po ga yozadi, compile_translations esa .po dan .mo yasaydi.
"""
import ast
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

PLURAL_FORMS = {
    "ru": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
    "en": "nplurals=2; plural=(n != 1);",
}
NPLURALS = {"ru": 3, "en": 2}


@dataclass
class Entry:
    msgid: str
    plural: str = ""
    msgstr: list = field(default_factory=lambda: [""])
    refs: list = field(default_factory=list)
    fuzzy: bool = False

    @property
    def key(self):
        return (self.msgid, self.plural)

    @property
    def translated(self):
        return not self.fuzzy and all(self.msgstr)


# — .po o‘qish va yozish —

def _unquote(s):
    s = s.strip()
    assert s.startswith('"') and s.endswith('"'), s
    return (s[1:-1].replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\"))


def _quote(s):
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\t", "\\t")
    if "\n" not in s:
        return f'"{s}"'
    lines = s.split("\n")
    parts = [line + "\\n" for line in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
    return '""\n' + "\n".join(f'"{p}"' for p in parts)


def read_po(path):
    """{(msgid, plural): Entry} — sarlavha (msgid "") ham qaytadi."""
    entries = {}
    if not Path(path).exists():
        return entries
    cur, last, fuzzy = None, None, False

    def flush():
        nonlocal cur, fuzzy
        if cur is not None:
            cur.fuzzy = fuzzy
            entries[cur.key] = cur
        cur, fuzzy = None, False

    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith("#,") and "fuzzy" in line:
            fuzzy = True
            continue
        if line.startswith("#"):
            continue
        if line.startswith("msgid_plural "):
            cur.plural, last = _unquote(line[13:]), "plural"
        elif line.startswith("msgid "):
            if cur is not None and last not in (None, "msgid"):
                flush()
            cur, last = Entry(_unquote(line[6:])), "msgid"
        elif line.startswith("msgstr["):
            idx = int(line[7:line.index("]")])
            while len(cur.msgstr) <= idx:
                cur.msgstr.append("")
            cur.msgstr[idx] = _unquote(line[line.index("]") + 1:])
            last = f"msgstr{idx}"
        elif line.startswith("msgstr "):
            cur.msgstr = [_unquote(line[7:])]
            last = "msgstr0"
        elif line.startswith('"'):
            text = _unquote(line)
            if last == "msgid":
                cur.msgid += text
            elif last == "plural":
                cur.plural += text
            elif last and last.startswith("msgstr"):
                cur.msgstr[int(last[6:])] += text
    flush()
    return entries


def header(lang):
    return (f"Project-Id-Version: Aevum\nLanguage: {lang}\nMIME-Version: 1.0\n"
            f"Content-Type: text/plain; charset=UTF-8\nContent-Transfer-Encoding: 8bit\n"
            f"Plural-Forms: {PLURAL_FORMS[lang]}\n")


def write_po(path, lang, entries):
    out = [f"# Aevum — {lang} tarjimasi. Asl matn (msgid) — o‘zbekcha.",
           "# Yangi matnlar: python manage.py make_translations; keyin: python manage.py compile_translations",
           'msgid ""', f"msgstr {_quote(header(lang))}", ""]
    for e in entries:
        for ref in e.refs[:3]:
            out.append(f"#: {ref}")
        if e.fuzzy:
            out.append("#, fuzzy")
        if "%(" in e.msgid or "%" in e.msgid.replace("%%", ""):
            out.append("#, python-format")
        out.append(f"msgid {_quote(e.msgid)}")
        if e.plural:
            out.append(f"msgid_plural {_quote(e.plural)}")
            for i, s in enumerate(e.msgstr):
                out.append(f"msgstr[{i}] {_quote(s)}")
        else:
            out.append(f"msgstr {_quote(e.msgstr[0])}")
        out.append("")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(out), encoding="utf-8", newline="\n")


def write_mo(path, lang, entries):
    """GNU .mo formatida yozadi (Python gettext va Django shuni o‘qiydi). Tarjimasizlar tashlab ketiladi."""
    pairs = [("", header(lang))]
    for e in entries.values():
        if not e.msgid or not e.translated:
            continue
        key = e.msgid + ("\0" + e.plural if e.plural else "")
        pairs.append((key, "\0".join(e.msgstr)))
    pairs.sort(key=lambda kv: kv[0].encode("utf-8"))
    ids = [k.encode("utf-8") for k, _v in pairs]
    strs = [v.encode("utf-8") for _k, v in pairs]
    n = len(pairs)
    keystart = 7 * 4 + 16 * n
    valuestart = keystart + sum(len(i) + 1 for i in ids)
    koffsets, voffsets, kpos, vpos = [], [], keystart, valuestart
    for i, s in zip(ids, strs):
        koffsets += [len(i), kpos]
        voffsets += [len(s), vpos]
        kpos += len(i) + 1
        vpos += len(s) + 1
    data = struct.pack("Iiiiiii", 0x950412DE, 0, n, 7 * 4, 7 * 4 + n * 8, 0, 0)
    data += struct.pack(f"{2 * n}i", *koffsets) + struct.pack(f"{2 * n}i", *voffsets)
    data += b"".join(i + b"\0" for i in ids) + b"".join(s + b"\0" for s in strs)
    Path(path).write_bytes(data)
    return n - 1


# — matnlarni yig‘ish —

PY_FUNCS = {"_": 1, "gettext": 1, "gettext_lazy": 1, "gettext_noop": 1, "ngettext": 2, "ngettext_lazy": 2}


def extract_python(path, rel):
    found = []
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else (
            node.func.attr if isinstance(node.func, ast.Attribute) else None)
        nargs = PY_FUNCS.get(name)
        if not nargs or len(node.args) < nargs:
            continue
        args = node.args[:nargs]
        if not all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in args):
            continue
        found.append((args[0].value, args[1].value if nargs == 2 else "", f"{rel}:{node.lineno}"))
    return found


def extract_template(engine, path, rel):
    """Shablonni Django’ning o‘zi bilan o‘qiydi — ish vaqtida qidiriladigan msgid aynan shu bo‘ladi."""
    from django.template import Template
    from django.templatetags.i18n import BlockTranslateNode, TranslateNode

    tpl = Template(Path(path).read_text(encoding="utf-8"), engine=engine)
    found = []
    for node in tpl.nodelist.get_nodes_by_type(TranslateNode):
        var = node.filter_expression.var
        literal = getattr(var, "literal", None)
        if isinstance(literal, str) and not node.message_context:
            found.append((str(literal), "", rel))
    for node in tpl.nodelist.get_nodes_by_type(BlockTranslateNode):
        if node.message_context:
            continue
        singular, _v = node.render_token_list(node.singular)
        plural = node.render_token_list(node.plural)[0] if node.plural and node.countervar else ""
        found.append((singular, plural, rel))
    return found


def collect(base_dir, engine):
    """Loyihadagi barcha tarjima qilinadigan matnlar: [(msgid, plural, joyi)] — birinchi uchragan tartibda."""
    base = Path(base_dir)
    items = []
    for app in ("config", "shop", "orders"):
        for path in sorted((base / app).rglob("*.py")):
            if "migrations" in path.parts or path.name == "po.py":
                continue
            items += extract_python(path, path.relative_to(base).as_posix())
    for path in sorted((base / "templates").rglob("*.html")):
        items += extract_template(engine, path, path.relative_to(base).as_posix())
    return items


MSG_VARS = re.compile(r"%\((\w+)\)s")


def same_vars(a, b):
    return sorted(MSG_VARS.findall(a)) == sorted(MSG_VARS.findall(b))
