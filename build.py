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
BS_CSS = ('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet" '
          'integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossorigin="anonymous">')
BS_JS = ('<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js" '
         'integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI" crossorigin="anonymous"></script>')
ICONS = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css">'
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">')

PARTS = [
    ("Foundations", "How we know, and what everyone already knows", range(1, 5)),
    ("The Evidence", "Prophecy, testimony, resurrection, and the cross", range(5, 9)),
    ("The Methods", "How Jesus and the apostles argued", range(9, 12)),
    ("Synthesis", "Bringing it together", range(12, 13)),
]
UNIT_ICONS = {1: "megaphone", 2: "lightbulb", 3: "stars", 4: "bank", 5: "hourglass-split", 6: "eye",
              7: "sunrise", 8: "heart-pulse", 9: "chat-quote", 10: "signpost-split", 11: "shield-check", 12: "compass"}


def part_of(n):
    for i, (name, _, rng) in enumerate(PARTS):
        if n in rng:
            return i + 1, name
    return 0, ""


# ---------- inline markdown ----------
def inline(text):
    t = html.escape(text, quote=False)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)} <i class="bi bi-box-arrow-up-right small"></i></a>', t)
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

units = []
for m in re.finditer(r"^## Unit (\d+): (.+?)\n(.*?)(?=^## |^---|\Z)", SRC, re.S | re.M):
    n, title, body = int(m.group(1)), m.group(2).strip(), m.group(3)
    fields = {}
    for fm in re.finditer(r"^- \*\*([^:*]+?)(?: \(([^)]*)\))?:\*\*\s*(.+)$", body, re.M):
        fields[fm.group(1)] = (fm.group(3).strip(), fm.group(2))
    units.append({"n": n, "title": title, "f": fields})


# ---------- layout ----------
def page(title, body, depth=0, active=""):
    up = "../" * depth
    nav = [("index.html", "Home", "home"), ("index.html#units", "Units", "units"),
           ("method.html", "Method", "method"), ("resources.html", "Resources", "resources")]
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
<link rel="stylesheet" href="{up}assets/site.css">
</head>
<body>
<a class="visually-hidden-focusable" href="#main">Skip to content</a>
<nav class="navbar navbar-expand-lg navbar-dark site-nav sticky-top">
  <div class="container">
    <a class="navbar-brand" href="{up}index.html"><i class="bi bi-book-half me-2"></i>{SITE_TITLE}</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav" aria-controls="nav" aria-expanded="false" aria-label="Toggle navigation"><span class="navbar-toggler-icon"></span></button>
    <div class="collapse navbar-collapse" id="nav"><ul class="navbar-nav ms-auto">{links}</ul></div>
  </div>
</nav>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="container d-md-flex justify-content-between align-items-center">
    <div><span class="brand-serif">{SITE_TITLE}</span> · {SITE_TAG}</div>
    <div class="small">“Always be ready to give a defense… with gentleness and respect.” — 1 Pet 3:15 (ESV)</div>
  </div>
</footer>
{BS_JS}
</body>
</html>
"""


def unit_card(u, up=""):
    _, part = part_of(u["n"])
    read = u["f"].get("Read", ("", None))[0]
    return f"""<div class="col-md-6 col-lg-4">
  <a class="card unit-card h-100" href="{up}units/unit-{u['n']:02d}.html">
    <div class="card-body">
      <div class="d-flex align-items-center mb-3">
        <span class="unit-num">{u['n']}</span>
        <i class="bi bi-{UNIT_ICONS.get(u['n'], 'book')} unit-icon ms-auto"></i>
      </div>
      <h3 class="h5 card-title">{html.escape(u['title'])}</h3>
      <p class="card-text small text-body-secondary mb-0">{inline(read[:110] + ('…' if len(read) > 110 else ''))}</p>
    </div>
  </a>
</div>"""


def method_steps():
    steps = []
    for m in re.finditer(r"^(\d)\. \*\*([^*]+)\*\*:?\s*(.*?)(?=^\d\. |\Z)", method_raw, re.S | re.M):
        txt = m.group(3).strip()
        safeguard = ""
        if ">" in txt:
            txt, sg = txt.split(">", 1)
            safeguard = f'<div class="callout callout-amber mt-2 small">{inline(sg.strip())}</div>'
        steps.append((m.group(1), m.group(2).strip().rstrip(":"), inline(txt.strip()) + safeguard))
    return steps


STEP_ICONS = ["book", "translate", "journal-text", "question-circle", "pencil-square", "heart"]


def build_index():
    cards = []
    for i, (pname, pdesc, rng) in enumerate(PARTS, 1):
        cs = "".join(unit_card(u) for u in units if u["n"] in rng)
        cards.append(f"""<div class="part-head"><span class="part-label">Part {i}</span><h3 class="h4 mb-0">{pname}</h3>
<p class="text-body-secondary mb-0">{pdesc}</p></div><div class="row g-4 mb-5">{cs}</div>""")
    steps = "".join(f"""<div class="col-sm-6 col-lg-4"><div class="step h-100"><i class="bi bi-{STEP_ICONS[int(n)-1]}"></i>
<div><div class="step-title">{n}. {t}</div><div class="small">{d}</div></div></div></div>""" for n, t, d in method_steps())
    body = f"""
<header class="hero">
  <div class="container">
    <div class="row align-items-center">
      <div class="col-lg-8">
        <p class="eyebrow">{SITE_TAG}</p>
        <h1 class="display-4 hero-title">{SITE_TITLE}</h1>
        <p class="lead hero-lead">How Scripture defends itself — and how God, Jesus and the apostles argued for the truth.</p>
        <div class="d-flex flex-wrap gap-2 mt-4">
          <a class="btn btn-gold btn-lg" href="units/unit-01.html">Begin Unit 1 <i class="bi bi-arrow-right"></i></a>
          <a class="btn btn-outline-light btn-lg" href="#units">View all units</a>
        </div>
      </div>
      <div class="col-lg-4 d-none d-lg-block">
        <blockquote class="hero-quote">“…but in your hearts honor Christ the Lord as holy, always being prepared to make a defense to anyone who asks you for a reason for the hope that is in you; yet do it with gentleness and respect.”<cite>1 Peter 3:15 (ESV)</cite></blockquote>
      </div>
    </div>
  </div>
</header>

<section class="stats-bar">
  <div class="container"><div class="row text-center g-3">
    <div class="col-6 col-md-3"><div class="stat-num">12</div><div class="stat-label">Units</div></div>
    <div class="col-6 col-md-3"><div class="stat-num">~1</div><div class="stat-label">Unit per week</div></div>
    <div class="col-6 col-md-3"><div class="stat-num">6</div><div class="stat-label">Steps per unit</div></div>
    <div class="col-6 col-md-3"><div class="stat-num">Free</div><div class="stat-label">Core resources</div></div>
  </div></div>
</section>

<section class="py-5">
  <div class="container">
    <div class="row g-5">
      <div class="col-lg-7">
        <h2 class="section-title">Purpose</h2>
        <p class="fs-5">{inline(purpose)}</p>
      </div>
      <div class="col-lg-5">
        <div class="callout callout-navy">
          <h2 class="h5"><i class="bi bi-clock me-2"></i>Pace &amp; workload</h2>
          <p class="mb-0">Self-paced, about one unit per week. Expect {inline(workload)}.</p>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="py-5 bg-parchment">
  <div class="container">
    <h2 class="section-title">The weekly rhythm</h2>
    <p class="text-body-secondary mb-4">Every unit follows the same six steps. <a href="method.html">Read the full method →</a></p>
    <div class="row g-3">{steps}</div>
  </div>
</section>

<section class="py-5" id="units">
  <div class="container">
    <h2 class="section-title mb-4">Units</h2>
    {''.join(cards)}
    <div class="callout callout-amber"><h3 class="h5"><i class="bi bi-award me-2"></i>Capstone (optional)</h3><p class="mb-0">{inline(capstone)}</p></div>
  </div>
</section>
"""
    return page("Home", body, active="home")


def build_unit(u):
    n, f = u["n"], u["f"]
    pnum, pname = part_of(n)
    prev_u = next((x for x in units if x["n"] == n - 1), None)
    next_u = next((x for x in units if x["n"] == n + 1), None)
    side = "".join(
        f'<a class="list-group-item list-group-item-action{" active" if x["n"] == n else ""}" href="unit-{x["n"]:02d}.html">'
        f'<span class="side-num">{x["n"]}</span>{html.escape(x["title"])}</a>' for x in units)

    def block(icon, title, inner, cls=""):
        return f'<section class="unit-block {cls}"><h2 class="block-title"><i class="bi bi-{icon}"></i>{title}</h2>{inner}</section>'

    blocks = []
    if "Read" in f:
        blocks.append(block("book", "Read", f'<p class="small text-body-secondary">Read each passage in context — the whole chapter, not just the verses. Links open the NET Bible.</p><div class="passages">{passages(f["Read"][0])}</div>'))
    if "Words" in f:
        blocks.append(block("translate", "Word study", f'<div class="words">{words(f["Words"][0])}</div>'
                            '<p class="small text-body-secondary mt-3 mb-0"><i class="bi bi-exclamation-triangle me-1"></i>Context, not a word\'s possible range, determines its meaning. Use <a href="https://www.stepbible.org" target="_blank" rel="noopener">STEP Bible</a> and the NET notes.</p>'))
    if "Supplement" in f:
        blocks.append(block("journal-text", "Supplement", f'<p class="mb-0">{inline(f["Supplement"][0])}</p>'))
    if "Questions" in f:
        blocks.append(block("question-circle", "Questions", questions(f["Questions"][0])))
    if "Posture" in f:
        blocks.append(f'<div class="callout callout-navy mb-4"><h2 class="h6 text-uppercase mb-1"><i class="bi bi-person-heart me-2"></i>Posture</h2><p class="mb-0">{inline(f["Posture"][0])}</p></div>')
    for key in ("Paper", "Final paper"):
        if key in f:
            text, note = f[key]
            label = "Final paper" if key == "Final paper" else "Paper · 1–2 pages"
            if note:
                label = f"Final paper · {html.escape(note)}"
            blocks.append(f'<div class="callout callout-amber mb-4"><h2 class="h6 text-uppercase mb-1"><i class="bi bi-pencil-square me-2"></i>{label}</h2><p class="mb-0">{inline(text)}</p></div>')
    blocks.append('<div class="callout callout-plain mb-4"><h2 class="h6 text-uppercase mb-1"><i class="bi bi-heart me-2"></i>Reflection · 1 page</h2><p class="mb-0">What did this show me about God?</p></div>')
    blocks.append(block("collection-play", "Audio &amp; video", '<p class="text-body-secondary mb-0"><i class="bi bi-hourglass me-1"></i>Podcast and video overviews for this unit are in production.</p>', "media-block"))

    pager = '<nav class="unit-pager d-flex justify-content-between mt-5" aria-label="Unit navigation">'
    pager += (f'<a class="btn btn-outline-navy" href="unit-{prev_u["n"]:02d}.html"><i class="bi bi-arrow-left"></i> Unit {prev_u["n"]}</a>' if prev_u else "<span></span>")
    pager += (f'<a class="btn btn-navy" href="unit-{next_u["n"]:02d}.html">Unit {next_u["n"]} <i class="bi bi-arrow-right"></i></a>' if next_u else '<a class="btn btn-navy" href="../index.html#units">All units</a>')
    pager += "</nav>"

    body = f"""
<header class="unit-hero">
  <div class="container">
    <nav aria-label="breadcrumb"><ol class="breadcrumb breadcrumb-light mb-2">
      <li class="breadcrumb-item"><a href="../index.html">Home</a></li>
      <li class="breadcrumb-item"><a href="../index.html#units">Part {pnum}: {pname}</a></li>
      <li class="breadcrumb-item active" aria-current="page">Unit {n}</li></ol></nav>
    <p class="eyebrow mb-1">Unit {n} of {len(units)}</p>
    <h1 class="display-6 hero-title mb-0"><i class="bi bi-{UNIT_ICONS.get(n, 'book')} me-2"></i>{html.escape(u['title'])}</h1>
    <div class="progress unit-progress mt-3" role="progressbar" aria-label="Course progress" aria-valuenow="{n}" aria-valuemin="0" aria-valuemax="{len(units)}">
      <div class="progress-bar" style="width:{n / len(units) * 100:.0f}%"></div></div>
  </div>
</header>
<div class="container py-5">
  <div class="row g-5">
    <aside class="col-lg-3 order-lg-2">
      <div class="sticky-lg-top side-wrap">
        <h2 class="h6 text-uppercase text-body-secondary">All units</h2>
        <div class="list-group list-group-flush side-list">{side}</div>
      </div>
    </aside>
    <article class="col-lg-9 order-lg-1">
      {''.join(blocks)}
      {pager}
    </article>
  </div>
</div>"""
    return page(f"Unit {n}: {u['title']}", body, depth=1, active="units")


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
            out.append(f'<li class="mb-2">{inline(line[2:])}')
    out.append("</ul></li>" if nested else "</li>")
    return '<ul class="resource-list">' + "".join(out) + "</ul>"


def build_resources():
    body = f"""
<header class="unit-hero"><div class="container"><p class="eyebrow mb-1">Library</p><h1 class="display-6 hero-title mb-0">Resources</h1></div></header>
<div class="container py-5"><div class="row"><div class="col-lg-9">
<p class="lead">Scripture is the final authority. Everything below serves the text.</p>
{md_list(resources_raw)}
</div></div></div>"""
    return page("Resources", body, active="resources")


def build_method():
    steps = "".join(f"""<div class="step step-lg mb-3"><i class="bi bi-{STEP_ICONS[int(n)-1]}"></i>
<div><h2 class="h5 mb-1">{n}. {t}</h2><div>{d}</div></div></div>""" for n, t, d in method_steps())
    body = f"""
<header class="unit-hero"><div class="container"><p class="eyebrow mb-1">How to study</p><h1 class="display-6 hero-title mb-0">Method</h1></div></header>
<div class="container py-5"><div class="row"><div class="col-lg-9">
<p class="lead">Every unit follows the same six steps. Expect {inline(workload)}.</p>
{steps}
<div class="callout callout-navy mt-4"><h2 class="h6 text-uppercase mb-1"><i class="bi bi-person-heart me-2"></i>The recurring question</h2>
<p class="mb-0">Every unit asks: <em>How should these texts shape the apologist's tone and conduct?</em></p></div>
</div></div></div>"""
    return page("Method", body, active="method")


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
