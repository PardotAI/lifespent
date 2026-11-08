#!/usr/bin/env python3
"""Build the static course site from SYLLABUS.md.

Usage: python3 build.py   (writes index.html, resources.html, units/*.html)
SYLLABUS.md is the single source of truth; edit it, then rebuild.
"""
import html
import re
from pathlib import Path
from htmlfmt import pretty
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
SRC = (ROOT / "SYLLABUS.md").read_text(encoding="utf-8")

SITE_TITLE = "Biblical Apologetics"
SITE_TAG = "A 12-Week Self-Study"
import hashlib
JS_VER = hashlib.md5((ROOT / "assets" / "progress.js").read_bytes()).hexdigest()[:8]
CSS_VER = hashlib.md5((ROOT / "assets" / "site.css").read_bytes()).hexdigest()[:8]  # cache-bust on change
SITE_URL = "https://www.lifespent.org/"
BS_CSS = ('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet" '
          'integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossorigin="anonymous">')
BS_JS = ('<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js" '
         'integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI" crossorigin="anonymous"></script>')
ICONS = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css">'
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500;600;700;800;900&family=Inter:wght@400;500;600&family=Noto+Serif:wght@400&family=Noto+Serif+Hebrew:wght@400&display=swap" rel="stylesheet">')
# Inter Tight is a free stand-in for Basecamp's Graphik (commercial).

PARTS = [
    ("Foundations", "Why defend the faith at all, and how do we know anything?", range(1, 5)),
    ("The Evidence", "What does the Bible offer as evidence, and how much weight does it carry?", range(5, 9)),
    ("The Methods", "How did Jesus and the apostles actually argue?", range(9, 12)),
    ("Synthesis", "What kind of apologist should all of this produce?", range(12, 13)),
]


def part_of(n):
    for i, (name, _, rng) in enumerate(PARTS):
        if n in rng:
            return i + 1, name
    return 0, ""


# ---------- inline markdown ----------
def inline(text):
    t = html.escape(text, quote=False)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               lambda m: f'<a class="go" href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)} <i class="bi bi-box-arrow-up-right small"></i></a>', t)
    t = re.sub(r"\[([^\]]+)\]\(([\w./-]+\.html)\)", r'<a class="go" href="\2">\1 <i class="bi bi-arrow-right small"></i></a>', t)
    t = re.sub(r"&lt;(https?://\S+?)&gt;", lambda m: link(m.group(1)), t)
    t = re.sub(r"(?<![\"'>=(])(https?://[^\s<)]+[^\s<).,;])", lambda m: link(m.group(1)), t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<em>\1</em>", t)
    return t


def link(url):
    label = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
    if len(label) > 48:
        label = label[:45] + "…"
    return f'<a href="{url}" target="_blank" rel="noopener">{label} <i class="bi bi-box-arrow-up-right small"></i></a>'


# ---------- Scripture links ----------
BOOK_RE = re.compile(r"^((?:[1-3] )?[A-Z][a-z]+)\s+(\d.*)$")



# bible.com (YouVersion) links, NET = version 107. USFM book codes.
USFM = {"Gen": "GEN", "Deut": "DEU", "1 Kgs": "1KI", "Job": "JOB", "Ps": "PSA", "Prov": "PRO", "Eccl": "ECC",
        "Isa": "ISA", "Jer": "JER", "Dan": "DAN", "Mic": "MIC", "Habakkuk": "HAB", "Matt": "MAT", "Luke": "LUK",
        "John": "JHN", "Acts": "ACT", "Rom": "ROM", "1 Cor": "1CO", "2 Cor": "2CO", "Eph": "EPH", "Phil": "PHP",
        "Col": "COL", "2 Tim": "2TI", "1 Pet": "1PE", "2 Pet": "2PE", "1 John": "1JN", "Jude": "JUD"}
ONE_CHAPTER = {"JUD"}


CHAPTERS = {"HAB": 3}                                  # whole-book readings
LAST_VERSE = {("ISA", 52): 15, ("ROM", 1): 32, ("1CO", 1): 31}  # for spans that cross a chapter


def _url(path):
    return f"https://www.bible.com/bible/107/{path}.NET"


def bible_links(book, ref):
    """Turn 'Isa' + '52:13–53:12' into one bible.com NET link per chapter:
    [('52:13–15', url), ('53:1–12', url)]. Verses in the same chapter stay one link."""
    code = USFM.get(book)
    if not code:
        raise SystemExit(f"build.py: no USFM code for book {book!r}; add it to USFM")
    ref = ref.replace("–", "-").replace(" ", "")
    if not ref:
        n = CHAPTERS.get(code)
        if not n:
            raise SystemExit(f"build.py: whole-book reading {book!r} needs a CHAPTERS entry")
        return [(f"ch. {c}", _url(f"{code}.{c}")) for c in range(1, n + 1)]
    if code in ONE_CHAPTER:
        return [(ref, _url(f"{code}.1.{ref}"))]
    links, cur_ch, verses = [], None, []

    def flush():
        if cur_ch is not None and verses:
            vs = ",".join(verses)
            links.append((f"{cur_ch}:{vs}", _url(f"{code}.{cur_ch}.{vs}")))

    for piece in ref.split(","):
        m = re.fullmatch(r"(\d+):(\d+)-(\d+):(\d+)", piece)
        if m:  # crosses chapters
            flush(); verses = []
            c1, v1, c2, v2 = map(int, m.groups())
            last = LAST_VERSE.get((code, c1))
            if not last:
                raise SystemExit(f"build.py: need LAST_VERSE[({code!r}, {c1})] to split {book} {piece}")
            links.append((f"{c1}:{v1}–{last}", _url(f"{code}.{c1}.{v1}-{last}")))
            for c in range(c1 + 1, c2):
                links.append((f"{c}", _url(f"{code}.{c}")))
            links.append((f"{c2}:1–{v2}", _url(f"{code}.{c2}.1-{v2}")))
            cur_ch = None
        elif ":" in piece:
            flush()
            cur_ch, v = piece.split(":", 1)
            verses = [v]
        elif cur_ch is not None:
            verses.append(piece)
        else:  # chapter or chapter range
            a, _, b = piece.partition("-")
            for c in range(int(a), int(b or a) + 1):
                links.append((f"{c}", _url(f"{code}.{c}")))
    flush()
    return [(lab.replace("-", "–"), u) for lab, u in links]


def split_top(line):
    """Split on ';' but not inside parentheses."""
    parts, depth, cur = [], 0, ""
    for ch in line:
        depth += (ch == "(") - (ch == ")")
        if ch == ";" and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return parts + [cur.strip()] if cur.strip() else parts


USFM_NAME = {"GEN": "Genesis", "DEU": "Deuteronomy", "1KI": "1 Kings", "JOB": "Job", "PSA": "Psalms", "PRO": "Proverbs",
             "ECC": "Ecclesiastes", "ISA": "Isaiah", "JER": "Jeremiah", "DAN": "Daniel", "MIC": "Micah", "HAB": "Habakkuk",
             "MAT": "Matthew", "LUK": "Luke", "JHN": "John", "ACT": "Acts", "ROM": "Romans", "1CO": "1 Corinthians",
             "2CO": "2 Corinthians", "EPH": "Ephesians", "PHP": "Philippians", "COL": "Colossians", "2TI": "2 Timothy",
             "1PE": "1 Peter", "2PE": "2 Peter", "1JN": "1 John", "JUD": "Jude"}


def net_notes(line):
    """One netbible.org link per chapter in a Read line (NET translator notes)."""
    seen, out = set(), []
    for u in re.findall(r'bible\.com/bible/107/([^"]+?)\.NET', passages(line)):
        code, ch = u.split(".")[:2]
        if (code, ch) in seen:
            continue
        seen.add((code, ch))
        name = USFM_NAME[code]
        out.append(f'<a href="https://netbible.org/bible/{name.replace(" ", "+")}+{ch}" target="_blank" rel="noopener">{name} {ch}</a>')
    return '<p class="net-notes"><span>NET translator notes:</span> ' + " · ".join(out) + "</p>" if out else ""


def passages(line):
    out, book = [], None
    for seg in split_top(line):
        note = ""
        nm = re.match(r"^(.*?)\s*\((.*)\)$", seg)
        if nm:
            seg, note = nm.group(1), nm.group(2)
        m = BOOK_RE.match(seg)
        ref = None
        if m and re.fullmatch(r"[\d:–,\s]+", m.group(2)):
            book, ref = m.group(1), seg
        elif re.fullmatch(r"(?:[1-3] )?[A-Z][a-z]+", seg):
            book, ref = seg, seg
        elif m:
            book = m.group(1)
        elif book and re.fullmatch(r"[\d:–,\s]+", seg):
            ref = f"{book} {seg}"
        label = html.escape(seg) + (f' <span class="passage-note">({html.escape(note)})</span>' if note else "")
        if ref:
            bk = book or ref
            rest = ref[len(bk):].strip() if ref.startswith(bk) else ref
            links = bible_links(bk, rest)
            if len(links) == 1:
                out.append(f'<a class="passage" href="{html.escape(links[0][1])}" '
                           f'target="_blank" rel="noopener"><i class="bi bi-book"></i> {label}</a>')
            else:
                parts = "".join(f'<a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(lab)}</a>' for lab, u in links)
                out.append(f'<span class="passage passage-group"><span><i class="bi bi-book"></i> {label}</span>'
                           f'<span class="chapters">{parts}</span></span>')
        else:
            out.append(f'<span class="passage passage-plain"><i class="bi bi-book"></i> {label}</span>')
    return "".join(out)


# Pronunciation guide. Stress the syllable in CAPS.
# Greek: classroom (Erasmian) pronunciation, the system most US seminaries teach.
# Hebrew: standard academic pronunciation.
PRONOUNCE = {
    "apologia": "ah-po-lo-GEE-ah", "elpis": "el-PEES", "prautēs": "prah-OO-tace", "phobos": "FOH-bos",
    "yirʾat YHWH": "yir-AHT ah-doh-NAI (the divine name is traditionally read aloud as Adonai)",
    "daʿat": "DAH-aht", "sophia": "so-FEE-ah", "gnōsis": "GNOH-sis", "alētheia": "ah-LAY-thay-ah",
    "phaneros": "fah-neh-ROSS", "katechō": "kah-TEH-khoh", "syneidēsis": "soon-AY-day-sis",
    "anapologētos": "ah-nah-po-LOG-ay-tos", "ʾĕlîl": "eh-LEEL", "ʿēd": "ADE", "rîb": "REEV",
    "nābîʾ": "nah-VEE", "plēroō": "play-ROH-oh", "dei": "DAY", "martys": "MAR-toos",
    "martyria": "mar-too-REE-ah", "autoptēs": "ow-TOP-tace", "asphaleia": "as-FAH-lay-ah",
    "mythos": "MOO-thos", "egeirō": "eh-GAY-roh", "anastasis": "ah-NAH-stah-sis", "ōphthē": "OHF-thay",
    "paradidōmi": "pah-rah-DEE-doh-mee", "aparchē": "ah-par-KHAY", "tām": "TAHM",
    "ʾĕmûnāh": "eh-moo-NAH", "dikaioō": "dee-kye-OH-oh", "peirazō": "pay-RAHD-zoh",
    "elenchō": "eh-LENG-khoh", "hypokritēs": "hoo-po-kree-TACE", "dialegomai": "dee-ah-LEG-oh-my",
    "peithō": "PAY-thoh", "paratithēmi": "pah-rah-TEE-thay-mee", "spermologos": "sper-mo-LOG-os",
    "apologeomai": "ah-po-lo-GEH-oh-my", "mainomai": "MY-no-my", "sōphrosynē": "soh-fro-SOO-nay",
    "aichmalōtizō": "aikh-mah-loh-TEED-zoh", "ochyrōma": "oh-KHOO-roh-mah",
    "epieikeia": "eh-pee-AY-kay-ah", "ēpios": "AY-pee-os", "halas": "HAH-las",
}


SCRIPT = {
    "apologia": "ἀπολογία",
    "elpis": "ἐλπίς",
    "prautēs": "πραΰτης",
    "phobos": "φόβος",
    "yirʾat YHWH": "יִרְאַת יְהוָה",
    "daʿat": "דַּעַת",
    "sophia": "σοφία",
    "gnōsis": "γνῶσις",
    "alētheia": "ἀλήθεια",
    "phaneros": "φανερός",
    "katechō": "κατέχω",
    "syneidēsis": "συνείδησις",
    "anapologētos": "ἀναπολόγητος",
    "ʾĕlîl": "אֱלִיל",
    "ʿēd": "עֵד",
    "rîb": "רִיב",
    "nābîʾ": "נָבִיא",
    "plēroō": "πληρόω",
    "dei": "δεῖ",
    "martys": "μάρτυς",
    "martyria": "μαρτυρία",
    "autoptēs": "αὐτόπτης",
    "asphaleia": "ἀσφάλεια",
    "mythos": "μῦθος",
    "egeirō": "ἐγείρω",
    "anastasis": "ἀνάστασις",
    "ōphthē": "ὤφθη",
    "paradidōmi": "παραδίδωμι",
    "aparchē": "ἀπαρχή",
    "tām": "תָּם",
    "ʾĕmûnāh": "אֱמוּנָה",
    "dikaioō": "δικαιόω",
    "peirazō": "πειράζω",
    "elenchō": "ἐλέγχω",
    "hypokritēs": "ὑποκριτής",
    "dialegomai": "διαλέγομαι",
    "peithō": "πείθω",
    "paratithēmi": "παρατίθημι",
    "spermologos": "σπερμολόγος",
    "apologeomai": "ἀπολογέομαι",
    "mainomai": "μαίνομαι",
    "sōphrosynē": "σωφροσύνη",
    "aichmalōtizō": "αἰχμαλωτίζω",
    "ochyrōma": "ὀχύρωμα",
    "epieikeia": "ἐπιείκεια",
    "ēpios": "ἤπιος",
    "halas": "ἅλας",
}


def script(term):
    parts = [SCRIPT.get(t.strip()) for t in term.split(" / ")]
    if not all(parts):
        raise SystemExit(f"build.py: no original script for word-study term {term!r}; add it to SCRIPT")
    return " / ".join(parts)


def say(term):
    parts = [PRONOUNCE.get(t.strip()) for t in term.split(" / ")]
    if not all(parts):
        raise SystemExit(f"build.py: no pronunciation for word-study term {term!r}; add it to PRONOUNCE")
    return " / ".join(parts)


def words(line):
    items = re.findall(r"\*([^*]+)\*((?:\s*/\s*\*[^*]+\*)*)\s*(\([^)]*\))?", line)
    out = []
    for main, alt, gloss in items:
        term = main + "".join(" / " + a for a in re.findall(r"\*([^*]+)\*", alt))
        g = html.escape(gloss.strip("()")) if gloss else ""
        pr = re.sub(r"\b([A-Z]{2,})\b", r"<b>\1</b>", html.escape(say(term)))
        sc = script(term)
        lang = "he" if re.search(r"[\u0590-\u05FF]", sc) else "grc"
        out.append(f'<span class="word"><span class="orig" lang="{lang}"{' dir="rtl"' if lang == "he" else ""}>{html.escape(sc)}</span>'
                   f'<span class="lemma">{html.escape(term)}</span>'
                   f'<span class="say" title="Pronunciation: stress the bold syllable">{pr}</span>'
                   + (f'<span class="gloss">{g}</span>' if g else "") + "</span>")
    return "".join(out) or inline(line)


def questions(line):
    qs = [q.strip() for q in re.findall(r"[^?]+\?", line)]
    if not qs:
        return f"<p>{inline(line)}</p>"
    return '<ol class="q-list">' + "".join(f"<li>{inline(q)}</li>" for q in qs) + "</ol>"


# ---------- parse ----------
def section(title):
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |^---|\Z)", SRC, re.S | re.M)
    return m.group(1).strip() if m else ""


header_line = SRC.splitlines()[2]
purpose = section("Purpose")
method_raw = section("Method (every unit)")
resources_raw = section("Free resources")
capstone = section("Capstone (optional)")
workload = re.search(r"\*\*Workload:\*\*\s*([^·]+)", header_line).group(1).strip()
workload = re.sub(r"^expect\s+", "", workload, flags=re.I)  # templates supply the verb

units = []
for m in re.finditer(r"^## Unit (\d+): (.+?)\n(.*?)(?=^## |^---|\Z)", SRC, re.S | re.M):
    n, title, body = int(m.group(1)), m.group(2).strip(), m.group(3)
    fields = {}
    for fm in re.finditer(r"^- \*\*([^:*]+?)(?: \(([^)]*)\))?:\*\*\s*(.+)$", body, re.M):
        fields[fm.group(1)] = (fm.group(3).strip(), fm.group(2))
    wm = re.search(r"^- \*\*Why these readings:\*\*\n((?:  - .*\n?)+)", body, re.M)
    why = [re.match(r"  - \*\*(.+?)\.\*\* (.*)", l).groups() for l in wm.group(1).splitlines()] if wm else []
    units.append({"n": n, "title": title, "f": fields, "why": why})


# ---------- layout ----------
def page(title, body, depth=0, active="", path="", unit=0):
    up = "../" * depth
    def cur(key):
        return ' active" aria-current="page' if key == active else ""
    cols = ""
    for i, (pname, _, rng) in enumerate(PARTS, 1):
        items = "".join(
            f'<li><a class="um-unit" href="{up}units/unit-{u["n"]:02d}.html" data-unit-link="{u["n"]}"'
            + (' aria-current="page"' if u["n"] == unit else "") + '>'
            f'<span class="um-n">{u["n"]:02d}</span><span class="um-t">{html.escape(short_title(u["title"]))}</span></a></li>'
            for u in units if u["n"] in rng)
        cols += f'<div class="um-part p{i}"><p class="um-head"><span class="dot"></span>Module {i} · {pname}</p><ul class="um-list">{items}</ul></div>'
    units_menu = (
        f'<li class="nav-item dropdown"><a class="nav-link dropdown-toggle{cur("units")}" href="{up}index.html#units" role="button" '
        f'data-bs-toggle="dropdown" data-bs-display="static" aria-expanded="false"><i class="bi bi-grid-3x3-gap"></i> Units</a>'
        f'<div class="dropdown-menu units-menu"><div class="um-grid">{cols}</div>'
        f'<div class="um-foot"><span class="note">✓ marks units you have finished in this browser.</span>'
        f'<a href="{up}index.html#units">All units and modules <i class="bi bi-arrow-right"></i></a></div></div></li>')
    links = (units_menu
             + f'<li class="nav-item"><a class="nav-link{cur("method")}" href="{up}method.html"><i class="bi bi-signpost-split"></i> Method</a></li>'
             + f'<li class="nav-item"><a class="nav-link{cur("resources")}" href="{up}resources.html"><i class="bi bi-book"></i> Resources</a></li>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<script>try{{var t=localStorage.getItem("lifespent.theme");if(t!=="light"&&t!=="dark")t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.setAttribute("data-bs-theme",t)}}catch(e){{}}</script>
<title>{html.escape(title)} · {SITE_TITLE} · LifeSpent</title>
<meta name="description" content="{SITE_TITLE}: {SITE_TAG}. A Scripture-governed study of how God, Jesus and the apostles argued for the truth.">
{FONTS}
{BS_CSS}
{ICONS}
<link rel="stylesheet" href="{up}assets/site.css?v={CSS_VER}">
<link rel="icon" type="image/svg+xml" href="{up}assets/favicon.svg">
<link rel="apple-touch-icon" href="{up}assets/icon-512.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="LifeSpent">
<meta property="og:title" content="{"LifeSpent: " + SITE_TITLE if title == "Home" else html.escape(title) + " · " + SITE_TITLE}">
<meta property="og:description" content="Spend your life going deeper in Scripture. {SITE_TAG}.">
<meta property="og:url" content="{SITE_URL}{path}">
<meta property="og:image" content="{SITE_URL}assets/og.png?v=89b5886e">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
</head>
<body data-root="{up}" data-unit="{unit or ''}">
<a class="visually-hidden-focusable" href="#main">Skip to content</a>
<nav class="navbar navbar-expand-md site-nav">
  <div class="container-xl">
    <a class="navbar-brand" href="{up}index.html" aria-label="LifeSpent: {SITE_TITLE}"><span class="ls-wm">Life<span>Spent</span></span><span class="brand-course">{SITE_TITLE}</span></a>
    <div class="nav-tools d-md-none"><button type="button" class="theme-toggle theme-toggle-m" data-theme-toggle aria-label="Switch to dark theme" title="Switch between light and dark"><i class="bi bi-moon"></i><i class="bi bi-sun"></i></button>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav" aria-controls="nav" aria-expanded="false" aria-label="Toggle navigation"><span class="navbar-toggler-icon"></span></button></div>
    <div class="collapse navbar-collapse" id="nav">
      <ul class="navbar-nav ms-auto align-items-md-center">{links}
        <li class="nav-item d-none d-md-block ms-md-1"><button type="button" class="theme-toggle" data-theme-toggle aria-label="Switch to dark theme" title="Switch between light and dark"><i class="bi bi-moon"></i><i class="bi bi-sun"></i></button></li>
        <li class="nav-item ms-md-3"><a class="btn btn-accent btn-sm-nav" href="{up}units/unit-01.html" data-resume-btn data-label-resume="Resume" data-label-done="Review"><span data-label>Begin</span></a></li>
      </ul>
    </div>
  </div>
</nav>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="container-xl">
    <p class="footer-verse">“…always be ready to give an answer to anyone who asks about the hope you possess. Yet do it with courtesy and respect…”</p>
    <p class="footer-ref">1 Peter 3:15–16 (NET)</p>
    <div class="footer-meta">
      <span><span class="ls-wm ls-wm-sm">Life<span>Spent</span></span> <em>Spend and be spent.</em> 2 Cor 12:15 · {SITE_TITLE}</span>
      <span class="footer-ack">Scripture quoted by permission. Quotations designated (NET) are from the NET Bible® copyright ©1996, 2019 by Biblical Studies Press, L.L.C. All rights reserved.</span>
      <span><a href="{up}index.html#units">Units</a> · <a href="{up}method.html">Method</a> · <a href="{up}resources.html">Resources</a> · <a href="#" data-reset-progress title="Your progress is saved only in this browser">Reset my progress</a> <a href="https://validator.w3.org/nu/?doc={quote(SITE_URL + path, safe="")}" rel="noopener" title="Check this page with the W3C HTML validator" class="w3c-badge"><img src="{up}assets/html5-logo.svg" alt="" width="20" height="20"><span><b>W3C</b> Valid HTML</span></a></span>
    </div>
  </div>
</footer>
{BS_JS}
<script src="{up}assets/progress.js?v={JS_VER}"></script>
</body>
</html>
"""


def method_steps():
    steps = []
    for m in re.finditer(r"^(\d)\. \*\*([^*]+)\*\*:?\s*(.*?)(?=^\d\. |\Z)", method_raw, re.S | re.M):
        txt = m.group(3).strip()
        safeguard = ""
        if ">" in txt:
            txt, sg = txt.split(">", 1)
            safeguard = f'<p class="note mt-2 mb-0">{inline(sg.strip())}</p>'
        txt = txt.strip()
        txt = txt[:1].upper() + txt[1:]
        steps.append((m.group(1), m.group(2).strip().rstrip(":"), inline(txt), safeguard))
    return steps


def sub_title(t):
    """The parenthetical part of a unit title, shown as a smaller subheading."""
    m = re.search(r"\(([^)]*)\)$", t)
    return m.group(1) if m else ""


def sub_html(u):
    s = sub_title(u["title"])
    return f'<span class="toc-sub">{html.escape(s)}</span>' if s else ""


def short_title(t):
    """Drop a parenthetical subtitle for compact labels, e.g. pager links."""
    return re.sub(r"\s*\(.*\)$", "", t)


def short_read(u, n=90):
    r = u["f"].get("Read", ("", None))[0]
    return r if len(r) <= n else r[:n].rsplit(";", 1)[0] + "; …"


def build_index():
    parts_html = []
    for i, (pname, pdesc, rng) in enumerate(PARTS, 1):
        rows = "".join(f"""
      <a class="toc-row" href="units/unit-{u['n']:02d}.html" data-unit-link="{u['n']}">
        <span class="toc-num">{u['n']:02d}</span>
        <span class="toc-body"><span class="toc-title">{html.escape(short_title(u['title']))}</span>{sub_html(u)}
        <span class="toc-read">{html.escape(short_read(u))}</span></span>
        <i class="bi bi-arrow-right toc-arrow"></i>
      </a>""" for u in units if u["n"] in rng)
        parts_html.append(f"""
    <div class="part p{i}">
      <div class="part-side"><span class="part-kicker"><span class="dot p{i}"></span>Module {i}</span><h3 class="part-name">{pname}</h3><p class="part-desc">{pdesc}</p></div>
      <div class="part-rows">{rows}</div>
    </div>""")

    phases = [
        ("Take it in", "bi-eye", [("bi-play-circle-fill", "Watch", "A short video overview sets the scene."),
                                   ("bi-book", "Read", "The primary passages, whole chapter in context.")]),
        ("Dig in", "bi-search", [("bi-translate", "Word study", "The key Greek and Hebrew terms."),
                                  ("bi-journal-bookmark", "Supplement", "One focused secondary reading."),
                                  ("bi-chat-square-text", "Questions", "Answered in your study journal.")]),
        ("Respond", "bi-pencil", [("bi-pencil-square", "Paper", "1–2 pages defending a thesis from the text."),
                                   ("bi-heart", "Reflection", "What did this show me about God?")]),
    ]
    steps = "".join(
        f'<li class="flow-phase"><p class="flow-head"><i class="bi {pic}"></i> {pname}</p><ul class="flow-steps">'
        + "".join(f'<li><span class="flow-ic"><i class="bi {ic}"></i></span><span><b>{st}</b><span>{d}</span></span></li>' for ic, st, d in items)
        + '</ul></li>' for pname, pic, items in phases)

    tiles = "".join(
        f'<a class="map-tile p{part_of(u["n"])[0]}" href="units/unit-{u["n"]:02d}.html" data-unit-link="{u["n"]}"><span class="map-n">{u["n"]:02d}</span>'
        f'<span class="map-t">{html.escape(short_title(u["title"]))}</span></a>' for u in units)
    legend = "".join(f'<span class="legend-item"><span class="dot p{i}"></span>{p[0]}</span>' for i, p in enumerate(PARTS, 1))

    body = f"""
<section class="hero">
  <div class="container-xl">
    <div class="row align-items-center g-4 g-lg-5">
      <div class="col-lg-6">
        <p class="kicker">{SITE_TAG}</p>
        <h1 class="hero-h1">Spend your life going deeper <span class="accent">in Scripture.</span></h1>
        <p class="hero-sub">{inline(purpose)}</p>
        <div class="d-flex flex-wrap gap-3 align-items-center mt-4">
          <a class="btn btn-accent btn-lg" href="units/unit-01.html" data-resume-btn data-label-resume="Resume Unit {{n}}" data-label-done="Review the course"><span data-label>Begin Unit 1</span> <i class="bi bi-arrow-right"></i></a>
          <a class="btn btn-quiet btn-lg" href="method.html">How it works</a>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="course-map" role="group" aria-label="Course map">
          <div class="map-grid">{tiles}</div>
          <div class="map-legend">{legend}</div>
        </div>
      </div>
    </div>
  </div>
</section>


<section class="section">
  <div class="container-xl">
    <h2 class="kicker mb-4">The Flow</h2>
    <ol class="flow">{steps}</ol>
    <p class="mt-4 mb-0"><a class="flow-more" href="method.html">See how each step works <i class="bi bi-arrow-right"></i></a></p>
  </div>
</section>

<section class="section section-alt" id="units">
  <div class="container-xl">
    <p class="kicker">The course</p>
    <h2 class="h2-big mb-5">Twelve units in four modules.</h2>
    {''.join(parts_html)}
    <div class="capstone">
      <span class="part-kicker">Optional capstone</span>
      <p class="mb-0">{inline(capstone)}</p>
    </div>
  </div>
</section>
"""
    return page("Home", body, active="home", path="")


def why_list(items):
    if not items:
        return ""
    rows = "".join(f'<li><span class="why-ref">{html.escape(r)}</span><span class="why-txt">{inline(t)}</span></li>' for r, t in items)
    return f'<h3 class="why-h">Why these readings</h3><ul class="why">{rows}</ul>'


# Published media per unit. Players load only when clicked (nothing third-party loads before that).
MEDIA = {
    1: {"video": ("vimeo", "1244297847", "4:14")},
    2: {"video": ("vimeo", "1244298253", "4:38")},
    3: {"video": ("vimeo", "1244295652", "5:17")},
    4: {"video": ("vimeo", "1244298711", "5:04")},
    5: {"video": ("vimeo", "1244651031", "6:00")},
    6: {"video": ("vimeo", "1244651034", "4:33")},
    7: {"video": ("vimeo", "1244651033", "4:45")},
    8: {"video": ("vimeo", "1244651032", "5:55")},
    9: {"video": ("vimeo", "1244720703", "4:42")},
    10: {"video": ("vimeo", "1244715370", "4:26")},
    11: {"video": ("vimeo", "1244889025", "4:28")},
    12: {"video": ("vimeo", "1244889834", "3:18")},
}


def video_feature(n):
    """Featured video at the top of the unit, BibleProject-style: our own poster image, click to play."""
    v = MEDIA.get(n, {}).get("video")
    if not v:
        return ""
    host, vid, length = v
    return (f'<figure class="u-video" id="video"><div class="media-player" data-{host}="{vid}" data-title="Unit {n} video overview">'
            f'<button type="button" class="media-play" aria-label="Play the Unit {n} video overview ({length})">'
            f'<img src="../assets/media/unit-{n:02d}.jpg" alt="" width="1280" height="720" loading="eager">'
            f'<span class="play-btn"><i class="bi bi-play-fill"></i></span><span class="dur">{length}</span></button></div>'
            f'<figcaption class="note">Video overview · {length}. Start here, then work through the readings below. <a href="../method.html#ai">AI-generated video: how we made it</a>.</figcaption></figure>')


def media_section(n):
    what = "Podcast overview" if MEDIA.get(n, {}).get("video") else "Podcast and video overviews"
    return (f'<div class="media-soon"><i class="bi bi-headphones"></i><div><strong>{what}</strong><br>'
            f'<span class="note">In production for this unit.</span></div></div>')


def build_unit(u):
    n, f = u["n"], u["f"]
    pnum, pname = part_of(n)
    prev_u = next((x for x in units if x["n"] == n - 1), None)
    next_u = next((x for x in units if x["n"] == n + 1), None)

    secs = []  # (id, label, html)
    if "Read" in f:
        secs.append(("read", "Read", f'<p class="note">Read each passage in context: this means reading the entire chapter, while paying close attention to the highlighted verses. Links open the NET Bible in the Bible app (bible.com).</p><div class="passages">{passages(f["Read"][0])}</div>' + net_notes(f["Read"][0]) + why_list(u["why"])))
    if "Words" in f:
        secs.append(("words", "Word study", f'<div class="words">{words(f["Words"][0])}</div><p class="note mt-3 mb-0">Say each word aloud and stress the <b class="say-b">bold</b> syllable. Greek follows the classroom (Erasmian) pronunciation most seminaries teach; Hebrew follows standard academic pronunciation. Other accepted systems exist (e.g., modern Greek, reconstructed Koine), so you may hear these said differently. The author\'s context decides the meaning.</p>'))
    if "Supplement" in f:
        secs.append(("supplement", "Supplement", f'<p class="mb-0">{inline(f["Supplement"][0])}</p>'))
    if "Questions" in f:
        secs.append(("questions", "Questions", questions(f["Questions"][0])))
    assign = []
    if "Posture" in f:
        assign.append(("Posture", "Ask of every text", inline(f["Posture"][0]), "tile-blue"))
    for key in ("Paper", "Final paper"):
        if key in f:
            text, note = f[key]
            sub = f"Final paper · {html.escape(note)}" if note else ("Final paper" if key == "Final paper" else "1–2 pages")
            assign.append(("Paper", sub, inline(text), "tile-yellow"))
    assign.append(("Reflection", "1 page", "What did this show me about God?", "tile-plain"))
    tiles = "".join(f'<div class="tile {cls}"><div class="tile-head"><span class="tile-label">{lab}</span><span class="tile-sub">{sub}</span></div><p class="mb-0">{txt}</p></div>'
                    for lab, sub, txt, cls in assign)
    secs.append(("write", "Write", f'<div class="tiles">{tiles}</div>'))
    secs.append(("media", "Podcast" if MEDIA.get(n, {}).get("video") else "Audio &amp; video", media_section(n)))

    toc = ('<a href="#video">Video</a>' if MEDIA.get(n, {}).get("video") else "") + "".join(f'<a href="#{sid}">{lab}</a>' for sid, lab, _ in secs)
    content = "".join(f'<section class="u-sec" id="{sid}"><h2 class="u-h2">{lab}</h2>{body}</section>' for sid, lab, body in secs)
    steps_ck = [("read", "Read the passages in context"), ("words", "Word study"), ("supplement", "Supplement"),
                ("questions", "Answer the questions"), ("paper", "Write the paper"), ("reflection", "Write the reflection")]
    tracker = ('<section class="tracker" aria-label="Your progress"><h2 class="u-h2">Your progress</h2>'
               '<p class="note">Saved only in this browser.</p><ul class="track-list">'
               + "".join(f'<li><label><input type="checkbox" data-step="{k}"> {v}</label></li>' for k, v in steps_ck)
               + '</ul><button type="button" class="btn btn-quiet" data-complete-btn aria-pressed="false"><i class="bi bi-check2-circle"></i> <span data-label>Mark unit complete</span></button></section>')
    pager = '<nav class="pager" aria-label="Unit navigation">'
    pager += (f'<a class="pager-link" href="unit-{prev_u["n"]:02d}.html"><span>← Unit {prev_u["n"]}</span>{html.escape(short_title(prev_u["title"]))}</a>' if prev_u else '<span></span>')
    pager += (f'<a class="pager-link text-end" href="unit-{next_u["n"]:02d}.html"><span>Unit {next_u["n"]} →</span>{html.escape(short_title(next_u["title"]))}</a>' if next_u else '<a class="pager-link text-end" href="../index.html#units"><span>Done →</span>All units</a>')
    pager += "</nav>"
    segs = "".join(f'<a href="unit-{x["n"]:02d}.html" data-unit-link="{x["n"]}" class="seg p{part_of(x["n"])[0]}{" on" if x["n"] <= n else ""}{" cur" if x["n"] == n else ""}"{' aria-current="page"' if x["n"] == n else ""} title="Unit {x["n"]}: {html.escape(short_title(x["title"]))}"></a>' for x in units)

    body = f"""
<header class="u-hero p{pnum}">
  <div class="container-xl">
    <nav aria-label="breadcrumb"><ol class="breadcrumb mb-3">
      <li class="breadcrumb-item"><a href="../index.html#units">Units</a></li>
      <li class="breadcrumb-item"><a href="../index.html#units">Module {pnum}: {pname}</a></li>
      <li class="breadcrumb-item active" aria-current="page">Unit {n}</li></ol></nav>
    <h1 class="u-h1">{html.escape(short_title(u['title']))}{f'<span class="visually-hidden">: </span><span class="u-h1-sub">{html.escape(sub_title(u["title"]))}</span>' if sub_title(u["title"]) else ""}</h1>
    <nav class="u-steps" aria-label="All units">{segs}</nav>
  </div>
</header>
<div class="unit-bar p{pnum} d-lg-none" data-unit-bar aria-hidden="true"><div class="container-xl"><span class="unit-bar-n">Unit {n}</span><span class="unit-bar-t">{html.escape(short_title(u['title']))}</span><span class="unit-bar-s" data-unit-bar-section></span></div></div>
<div class="container-xl">
  <div class="row g-5">
    <aside class="col-lg-3 d-none d-lg-block">
      <div class="u-toc"><a class="toc-unit p{pnum}" href="#main"><span class="toc-unit-n">Unit {n} · Module {pnum}</span><span class="toc-unit-t">{html.escape(short_title(u['title']))}</span></a><p class="part-kicker">On this page</p>{toc}</div>
    </aside>
    <div class="col-lg-8 u-article">
      {video_feature(n)}
      {content}
      {tracker}
      {pager}
    </div>
  </div>
</div>"""
    return page(f"Unit {n}: {short_title(u['title'])}" + (f": {sub_title(u['title'])}" if sub_title(u["title"]) else ""), body, depth=1, active="units", path=f"units/unit-{n:02d}.html", unit=n)


def md_list(raw):
    out, nested = [], False
    for line in raw.splitlines():
        if line.startswith("  - "):
            if not nested:
                out.append('<ul class="mt-2">')
                nested = True
            out.append(f"<li>{inline(line[4:])}</li>")
        elif line.startswith("- "):
            if nested:
                out.append("</ul></li>")
                nested = False
            elif out:
                out.append("</li>")
            out.append(f'<li>{inline(line[2:])}')
    out.append("</ul></li>" if nested else "</li>")
    return '<ul class="res-list">' + "".join(out) + "</ul>"


def simple_page(kicker, title, lead, inner, active):
    body = f"""
<header class="u-hero plain"><div class="container-xl"><p class="kicker mb-2">{kicker}</p><h1 class="u-h1">{title}</h1>
<p class="hero-sub mt-3 mb-0">{lead}</p></div></header>
<div class="container-xl"><div class="row"><div class="col-lg-9 u-article">{inner}</div></div></div>"""
    return page(re.sub("<[^>]+>", "", title), body, active=active, path=f"{active}.html")


# Resources page data. Keep in step with "## Free resources" in SYLLABUS.md.
RES_CORE = [
    ("bi-book", "NET Bible", "Bible + translator notes", "https://netbible.org",
     "The course translation. Read every passage here, and use the translator notes to see why a verse is rendered the way it is.", "Every unit: Read"),
    ("bi-translate", "STEP Bible", "Greek and Hebrew tools", "https://www.stepbible.org",
     "Look up the original word behind an English one, see where else it appears, and check its range of meaning.", "Every unit: Word study"),
]
RES_DEEPER = [
    ("bi-headphones", "The Table podcast", "Podcast · DTS", "https://voice.dts.edu/tablepodcast/",
     "Short conversations with Dallas Seminary scholars on faith questions.", [1, 6, 7]),
    ("bi-file-earmark-text", "Poythress, Logic", "Book · free PDF", "https://frame-poythress.org/wp-content/uploads/2013/07/BLogicFinal.pdf",
     "A God-centered approach to logic: why reasoning works and how arguments fail.", [2, 9]),
    ("bi-bank", "CCEL library", "Classic texts · public domain", "https://www.ccel.org",
     "Calvin's Institutes, Warfield, Machen and Pascal, free to read online.", [2, 3]),
    ("bi-journal-text", "Frame and Poythress articles", "Articles", "https://frame-poythress.org",
     "Free essays on apologetics and theology, including Frame on presuppositional apologetics.", [4]),
    ("bi-camera-video", "DTS free courses", "Video lectures · DTS", "https://voice.dts.edu/free-courses/",
     "Full graduate courses, including Bible introduction, the Gospels and Acts, and Greek and Hebrew basics.", [6, 8]),
    ("bi-bookmark", "Constable's Expository Notes", "Commentary · DTS", "https://soniclight.com/constable-notes/",
     "Verse-by-verse notes on every book of the Bible from Dr. Thomas Constable.", [10]),
    ("bi-mortarboard", "Essentials of Christian Apologetics", "Course · BiblicalTraining.org", "https://www.biblicaltraining.org/learn/foundations/th201-essentials-of-christian-apologetics",
     "Ronald Nash's survey course, a good overview if you want the wider field.", []),
]
RES_BUY = [
    ("Geisler", "Baker Encyclopedia of Christian Apologetics", "A reference in the classical and evidential tradition."),
    ("Bahnsen", "Always Ready", "A short presuppositional introduction; its Acts 17 chapter pairs with Unit 10."),
    ("Frame", "Apologetics: A Justification of Christian Belief", "A fuller presuppositional treatment."),
]


def build_resources():
    def host(url):
        return re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    core = "".join(
        f'<a class="r-core" href="{url}" rel="noopener"><span class="r-icon"><i class="bi {ic}"></i></span>'
        f'<span class="r-body"><span class="r-type">{typ}</span><span class="r-name">{name}</span><span class="r-desc">{desc}</span>'
        f'<span class="r-use"><i class="bi bi-check2-circle"></i> {use}</span></span>'
        f'<span class="r-go">{host(url)} <i class="bi bi-box-arrow-up-right"></i></span></a>'
        for ic, name, typ, url, desc, use in RES_CORE)
    def tags(ns):
        if not ns:
            return '<span class="r-tag r-tag-plain">Optional overview</span>'
        return "".join(f'<a class="r-tag p{part_of(n)[0]}" href="units/unit-{n:02d}.html">Unit {n}</a>' for n in ns)
    deeper = "".join(
        f'<li class="r-card"><span class="r-icon r-icon-sm"><i class="bi {ic}"></i></span><div class="r-body">'
        f'<p class="r-type">{typ}</p><h3 class="r-name"><a href="{url}" rel="noopener" class="stretched-link">{name}</a></h3>'
        f'<p class="r-desc">{desc}</p><div class="r-tags">{tags(ns)}</div></div></li>'
        for ic, name, typ, url, desc, ns in RES_DEEPER)
    buy = "".join(f'<li><b>{a}</b>, <em>{b}</em>. {c}</li>' for a, b, c in RES_BUY)
    body = f"""
<header class="m-hero"><div class="container-xl"><div class="row justify-content-center"><div class="col-lg-9">
<p class="kicker mb-2">Library</p><h1 class="hero-h1 mb-3">Resources</h1>
<p class="hero-sub mb-2">Scripture is the final authority. Everything here serves the text, not the other way around.</p>
<p class="note mb-0"><i class="bi bi-gift"></i> Everything on this page is free unless it's marked as a purchase.</p>
</div></div></div></header>
<div class="container-xl"><div class="row justify-content-center"><div class="col-lg-9">
<section class="r-sec"><h2 class="r-h2">Foundational</h2><p class="note mb-3">You'll use these two every week.</p><div class="r-core-grid">{core}</div></section>
<section class="r-sec"><h2 class="r-h2">Go deeper</h2><p class="note mb-3">Each unit's supplement comes from one of these. The tags show where.</p><ul class="r-grid">{deeper}</ul></section>
<div class="r-sec"><details class="r-buy"><summary><span class="r-h2 mb-0">Optional purchases</span><i class="bi bi-chevron-down"></i></summary><ul class="r-buy-list">{buy}</ul></details></div>
</div></div></div>"""
    return page("Resources", body, active="resources", path="resources.html")


def build_method():
    meta = {  # icon, what you produce, where it lives on each unit page
        "Read": ("bi-book", "Notes on the passages", "read", "Day 1", "Start with the unit's video overview"),
        "Word study": ("bi-translate", "A short word list", "words", "Day 2", ""),
        "Supplement": ("bi-journal-bookmark", "Notes from one reading", "supplement", "Day 3", ""),
        "Questions": ("bi-chat-square-text", "Journal answers", "questions", "Day 4", ""),
        "Paper": ("bi-pencil-square", "A 1–2 page paper", "write", "Days 5–6", "Draft one day, finish the next"),
        "Reflection": ("bi-heart", "A 1-page reflection", "write", "Day 7", ""),
    }
    items = ""
    for n, title, desc, sg in method_steps():
        icon, out, sec, day, tip = meta.get(title, ("bi-circle", "", "read", "", ""))
        callout = sg.replace('<p class="note mt-2 mb-0">', '<div class="m-callout"><i class="bi bi-shield-check"></i><p class="mb-0">').replace("</p>", "</p></div>") if sg else ""
        items += (f'<li class="m-step"><span class="m-dot"></span>'
                  f'<div class="m-card"><div class="m-top"><h3 class="m-title"><span class="m-ic"><i class="bi {icon}"></i></span>{title}</h3><span class="m-day"><i class="bi bi-calendar3"></i> {day}</span></div>'
                  f'<p class="m-desc">{desc}</p>' + (f'<p class="m-tip"><i class="bi bi-lightbulb"></i> {tip}</p>' if tip else "") + f'{callout}'
                  f'<p class="m-out"><span><i class="bi bi-check2-square"></i> Your homework: <b>{out}</b></span>'
                  f'<span class="m-where">On each unit page: “{ {"read": "Read", "words": "Word study", "supplement": "Supplement", "questions": "Questions", "write": "Write"}[sec] }”</span></p></div></li>')
    body = f"""
<header class="m-hero"><div class="container-xl"><div class="row justify-content-center g-4">
<div class="col-lg-9"><p class="kicker mb-2">How to study</p><h1 class="hero-h1 mb-3">One rhythm, <span class="accent">every week.</span></h1>
<p class="hero-sub mb-2">Every unit follows the same steps, so your effort goes into the text instead of the format.</p>
<p class="note mb-4"><i class="bi bi-clock"></i> Expect {inline(workload)}.</p>
<div class="d-flex flex-wrap gap-2"><a class="btn btn-accent btn-lg" href="units/unit-01.html" data-resume-btn data-label-resume="Resume Unit {n}" data-label-done="Review the course"><span data-label>Begin Unit 1</span> <i class="bi bi-arrow-right"></i></a><a class="btn btn-quiet btn-lg" href="index.html#units">See all units</a></div></div>
</div></div></header>
<div class="container-xl"><div class="row justify-content-center g-5">
<div class="col-lg-9"><h2 class="h2-big mb-2">Step by step</h2><p class="note mb-4"><i class="bi bi-calendar-week"></i> Each step shows a suggested day. It's a pace, not a rule; heavier units may need extra time.</p><ol class="m-timeline">{items}</ol></div>
</div></div>
<section class="m-ai" id="ai"><div class="container-xl"><div class="row justify-content-center"><div class="col-lg-9"><div class="m-ai-box">
<h2 class="m-ai-h"><i class="bi bi-stars"></i> How these materials were made</h2>
<p>The unit videos were created with Google NotebookLM, an AI tool powered by Gemini, and grounded in each unit’s NET Bible readings and course material. The narration and visuals are AI-generated.</p>
<p class="mb-0"><strong>Scripture is the final authority.</strong> The videos are a starting point, not a substitute for reading the passages yourself. If a video and the text ever seem to disagree, go with the text.</p>
</div>
<div class="m-about" id="about"><h2 class="m-ai-h"><i class="bi bi-person"></i> About the author</h2>
<p class="mb-0">Thomas Hastings, Ph.D., built LifeSpent for people who want to grow deeper in their faith and learn to share it well. The course examines how God, Christ, and the apostles presented the truth to nonbelievers and to believers who had gone astray, with Scripture as the final authority throughout. He reviewed and verified every unit: the content against the text, quotations against the NET, and readings that scholars debate labeled as debated. Learn more about him at <a href="https://thomashastings.com" rel="noopener">thomashastings.com</a>.</p>
</div></div></div></div></section>
<section class="m-cta"><div class="container-xl"><div class="row justify-content-center"><div class="col-lg-9"><div class="m-cta-box"><div><h2 class="h2-big mb-2">Ready to start?</h2><p class="mb-0">Your progress is saved in this browser, so you can pick up where you left off.</p></div>
<a class="btn btn-accent btn-lg" href="units/unit-01.html" data-resume-btn data-label-resume="Resume Unit {n}" data-label-done="Review the course"><span data-label>Begin Unit 1</span> <i class="bi bi-arrow-right"></i></a></div></div></div></div></section>"""
    return page("Method", body, active="method", path="method.html")


def main():
    (ROOT / "units").mkdir(exist_ok=True)
    (ROOT / "index.html").write_text(pretty(build_index()), encoding="utf-8")
    (ROOT / "resources.html").write_text(pretty(build_resources()), encoding="utf-8")
    (ROOT / "method.html").write_text(pretty(build_method()), encoding="utf-8")
    for u in units:
        (ROOT / "units" / f"unit-{u['n']:02d}.html").write_text(pretty(build_unit(u)), encoding="utf-8")
    print(f"built index, method, resources, {len(units)} units")


if __name__ == "__main__":
    main()
