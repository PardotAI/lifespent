#!/usr/bin/env python3
"""Build the static course site from SYLLABUS.md.

Usage: python3 build.py   (writes index.html, resources.html, units/*.html)
SYLLABUS.md is the single source of truth; edit it, then rebuild.
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = (ROOT / "SYLLABUS.md").read_text(encoding="utf-8")

SITE_TITLE = "Biblical Apologetics"
SITE_TAG = "A 12-Week Self-Study"
import hashlib
CSS_VER = hashlib.md5((ROOT / "assets" / "site.css").read_bytes()).hexdigest()[:8]  # cache-bust on change
SITE_URL = "https://pardotai.github.io/lifespent/"  # change to https://lifespent.org/ when the domain moves
BS_CSS = ('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet" '
          'integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossorigin="anonymous">')
BS_JS = ('<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js" '
         'integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI" crossorigin="anonymous"></script>')
ICONS = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css">'
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500;600;700;800;900&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">')
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
            q = re.sub(r",\s*", ",", ref).replace("–", "-").replace(" ", "+")
            out.append(f'<a class="passage" href="https://www.biblegateway.com/passage/?search={q}&amp;version=NET" '
                       f'target="_blank" rel="noopener"><i class="bi bi-book"></i> {label}</a>')
        else:
            out.append(f'<span class="passage passage-plain"><i class="bi bi-book"></i> {label}</span>')
    return "".join(out)


def words(line):
    items = re.findall(r"\*([^*]+)\*((?:\s*/\s*\*[^*]+\*)*)\s*(\([^)]*\))?", line)
    out = []
    for main, alt, gloss in items:
        term = main + "".join(" / " + a for a in re.findall(r"\*([^*]+)\*", alt))
        g = html.escape(gloss.strip("()")) if gloss else ""
        out.append(f'<span class="word"><span class="lemma">{html.escape(term)}</span>'
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
    units.append({"n": n, "title": title, "f": fields})


# ---------- layout ----------
def page(title, body, depth=0, active="", path=""):
    up = "../" * depth
    nav = [("index.html#units", "Units", "units"), ("method.html", "Method", "method"),
           ("resources.html", "Resources", "resources")]
    links = "".join(
        f'<li class="nav-item"><a class="nav-link{" active" if key == active else ""}" href="{up}{href}">{label}</a></li>'
        for href, label, key in nav)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · {SITE_TITLE}</title>
<meta name="description" content="{SITE_TITLE}: {SITE_TAG}. A Scripture-governed study of how God, Jesus and the apostles argued for the truth.">
{FONTS}
{BS_CSS}
{ICONS}
<link rel="stylesheet" href="{up}assets/site.css?v={CSS_VER}">
<link rel="icon" type="image/svg+xml" href="{up}assets/favicon.svg">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_TITLE}">
<meta property="og:title" content="{html.escape(title)} · {SITE_TITLE}">
<meta property="og:description" content="Learn how Scripture defends itself. {SITE_TAG}.">
<meta property="og:url" content="{SITE_URL}{path}">
<meta property="og:image" content="{SITE_URL}assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
</head>
<body>
<a class="visually-hidden-focusable" href="#main">Skip to content</a>
<nav class="navbar navbar-expand-md site-nav">
  <div class="container-xl">
    <a class="navbar-brand" href="{up}index.html"><span class="brand-mark"><i class="bi bi-book-half"></i></span>{SITE_TITLE}</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav" aria-controls="nav" aria-expanded="false" aria-label="Toggle navigation"><span class="navbar-toggler-icon"></span></button>
    <div class="collapse navbar-collapse" id="nav">
      <ul class="navbar-nav ms-auto align-items-md-center">{links}
        <li class="nav-item ms-md-3"><a class="btn btn-accent btn-sm-nav" href="{up}units/unit-01.html">Begin</a></li>
      </ul>
    </div>
  </div>
</nav>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="container-xl">
    <p class="footer-verse">“Always being prepared to make a defense to anyone who asks you for a reason for the hope that is in you; yet do it with gentleness and respect.”</p>
    <p class="footer-ref">1 Peter 3:15 (ESV)</p>
    <div class="footer-meta">
      <span><strong>{SITE_TITLE}</strong> — {SITE_TAG}</span>
      <span><a href="{up}index.html#units">Units</a> · <a href="{up}method.html">Method</a> · <a href="{up}resources.html">Resources</a></span>
    </div>
  </div>
</footer>
{BS_JS}
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
      <a class="toc-row" href="units/unit-{u['n']:02d}.html">
        <span class="toc-num">{u['n']:02d}</span>
        <span class="toc-body"><span class="toc-title">{html.escape(u['title'])}</span>
        <span class="toc-read">{html.escape(short_read(u))}</span></span>
        <i class="bi bi-arrow-right toc-arrow"></i>
      </a>""" for u in units if u["n"] in rng)
        parts_html.append(f"""
    <div class="part p{i}">
      <div class="part-side"><span class="part-kicker"><span class="dot p{i}"></span>Part {i}</span><h3 class="part-name">{pname}</h3><p class="part-desc">{pdesc}</p></div>
      <div class="part-rows">{rows}</div>
    </div>""")

    steps = "".join(f"""
      <div class="col-sm-6 col-lg-4"><div class="rhythm">
        <span class="rhythm-num">{n}</span><h3 class="rhythm-title">{t}</h3><p class="mb-0">{d}</p>{sg}
      </div></div>""" for n, t, d, sg in method_steps())

    tiles = "".join(
        f'<a class="map-tile p{part_of(u["n"])[0]}" href="units/unit-{u["n"]:02d}.html"><span class="map-n">{u["n"]:02d}</span>'
        f'<span class="map-t">{html.escape(short_title(u["title"]))}</span></a>' for u in units)
    legend = "".join(f'<span class="legend-item"><span class="dot p{i}"></span>{p[0]}</span>' for i, p in enumerate(PARTS, 1))

    body = f"""
<section class="hero">
  <div class="container-xl">
    <div class="row align-items-center g-4 g-lg-5">
      <div class="col-lg-6">
        <p class="kicker">{SITE_TAG}</p>
        <h1 class="hero-h1">Learn how Scripture <span class="accent">defends itself.</span></h1>
        <p class="hero-sub">God makes arguments in Scripture. So do Jesus and the apostles. You will read those arguments in context, one unit a week, and work out what they ask of you.</p>
        <div class="d-flex flex-wrap gap-3 align-items-center mt-4">
          <a class="btn btn-accent btn-lg" href="units/unit-01.html">Begin Unit 1 <i class="bi bi-arrow-right"></i></a>
          <a class="btn btn-quiet btn-lg" href="method.html">How it works</a>
        </div>
        <ul class="meta-row">
          <li><strong>12</strong> units</li><li><strong>4</strong> parts</li><li><strong>~1</strong> per week</li><li><strong>Free</strong> resources</li>
        </ul>
      </div>
      <div class="col-lg-6">
        <div class="course-map" aria-label="Course map">
          <div class="map-grid">{tiles}</div>
          <div class="map-legend">{legend}</div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="band">
  <div class="container-xl">
    <div class="row g-4 g-lg-5 align-items-start">
      <div class="col-lg-5"><h2 class="h2-big">Scripture is the final authority.</h2></div>
      <div class="col-lg-7">
        <p class="lead-ink">{inline(purpose)}</p>
        <p class="note mb-0"><strong>Workload:</strong> expect {inline(workload)}.</p>
      </div>
    </div>
  </div>
</section>

<section class="section">
  <div class="container-xl">
    <p class="kicker">Every week</p>
    <h2 class="h2-big mb-5">Six steps. <span class="accent">Same rhythm</span> every unit.</h2>
    <div class="row g-4">{steps}
    </div>
  </div>
</section>

<section class="section section-alt" id="units">
  <div class="container-xl">
    <p class="kicker">The course</p>
    <h2 class="h2-big mb-5">Twelve units in four parts.</h2>
    {''.join(parts_html)}
    <div class="capstone">
      <span class="part-kicker">Optional capstone</span>
      <p class="mb-0">{inline(capstone)}</p>
    </div>
  </div>
</section>
"""
    return page("Home", body, active="home", path="")


def build_unit(u):
    n, f = u["n"], u["f"]
    pnum, pname = part_of(n)
    prev_u = next((x for x in units if x["n"] == n - 1), None)
    next_u = next((x for x in units if x["n"] == n + 1), None)

    secs = []  # (id, label, html)
    if "Read" in f:
        secs.append(("read", "Read", f'<p class="note">Read each passage in context: the whole chapter, not just the verses. Links open the NET Bible.</p><div class="passages">{passages(f["Read"][0])}</div>'))
    if "Words" in f:
        secs.append(("words", "Word study", f'<div class="words">{words(f["Words"][0])}</div><p class="note mt-3 mb-0">Context, not a word\'s possible range, decides its meaning. Use <a href="https://www.stepbible.org" target="_blank" rel="noopener">STEP Bible</a> and the NET notes.</p>'))
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
    secs.append(("media", "Audio &amp; video", '<div class="media-soon"><i class="bi bi-headphones"></i><div><strong>Podcast and video overviews</strong><br><span class="note">In production for this unit.</span></div></div>'))

    toc = "".join(f'<a href="#{sid}">{lab}</a>' for sid, lab, _ in secs)
    content = "".join(f'<section class="u-sec" id="{sid}"><h2 class="u-h2">{lab}</h2>{body}</section>' for sid, lab, body in secs)
    pager = '<nav class="pager" aria-label="Unit navigation">'
    pager += (f'<a class="pager-link" href="unit-{prev_u["n"]:02d}.html"><span>← Unit {prev_u["n"]}</span>{html.escape(short_title(prev_u["title"]))}</a>' if prev_u else '<span></span>')
    pager += (f'<a class="pager-link text-end" href="unit-{next_u["n"]:02d}.html"><span>Unit {next_u["n"]} →</span>{html.escape(short_title(next_u["title"]))}</a>' if next_u else '<a class="pager-link text-end" href="../index.html#units"><span>Done →</span>All units</a>')
    pager += "</nav>"
    segs = "".join(f'<a href="unit-{x["n"]:02d}.html" class="seg p{part_of(x["n"])[0]}{" on" if x["n"] <= n else ""}{" cur" if x["n"] == n else ""}" title="Unit {x["n"]}: {html.escape(x["title"])}"></a>' for x in units)

    body = f"""
<header class="u-hero p{pnum}">
  <div class="container-xl">
    <nav aria-label="breadcrumb"><ol class="breadcrumb mb-3">
      <li class="breadcrumb-item"><a href="../index.html#units">Units</a></li>
      <li class="breadcrumb-item"><a href="../index.html#units">Part {pnum}: {pname}</a></li>
      <li class="breadcrumb-item active" aria-current="page">Unit {n}</li></ol></nav>
    <p class="kicker mb-2">Unit {n} of {len(units)}</p>
    <h1 class="u-h1">{html.escape(u['title'])}</h1>
    <div class="u-steps" role="progressbar" aria-label="Course progress" aria-valuenow="{n}" aria-valuemin="0" aria-valuemax="{len(units)}">{segs}</div>
  </div>
</header>
<div class="container-xl">
  <div class="row g-5">
    <aside class="col-lg-3 d-none d-lg-block">
      <div class="u-toc"><p class="part-kicker">On this page</p>{toc}</div>
    </aside>
    <article class="col-lg-8 u-article">
      {content}
      {pager}
    </article>
  </div>
</div>"""
    return page(f"Unit {n}: {u['title']}", body, depth=1, active="units", path=f"units/unit-{n:02d}.html")


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


def build_resources():
    return simple_page("Library", "Resources", "Scripture is the final authority. Everything on this page is here to serve the text, not to replace it.",
                       md_list(resources_raw), "resources")


def build_method():
    steps = "".join(f"""<div class="rhythm rhythm-row"><span class="rhythm-num">{n}</span><div><h2 class="rhythm-title">{t}</h2><p class="mb-0">{d}</p>{sg}</div></div>"""
                    for n, t, d, sg in method_steps())
    inner = steps + '<div class="tile tile-blue mt-4"><div class="tile-head"><span class="tile-label">The recurring question</span></div><p class="mb-0">Every unit asks: <em>How should these texts shape the apologist\'s tone and conduct?</em></p></div>'
    return simple_page("How to study", "Method", f"Every unit uses the same six steps, so your effort goes into the text instead of the format. Expect {inline(workload)}.", inner, "method")


def main():
    (ROOT / "units").mkdir(exist_ok=True)
    (ROOT / "index.html").write_text(build_index(), encoding="utf-8")
    (ROOT / "resources.html").write_text(build_resources(), encoding="utf-8")
    (ROOT / "method.html").write_text(build_method(), encoding="utf-8")
    for u in units:
        (ROOT / "units" / f"unit-{u['n']:02d}.html").write_text(build_unit(u), encoding="utf-8")
    print(f"built index, method, resources, {len(units)} units")


if __name__ == "__main__":
    main()
