# Biblical Apologetics — A 12-Week Self-Study

Static course site (Bootstrap 5.3, no build tooling beyond Python 3).

- Source of truth: `SYLLABUS.md`
- Rebuild: `python3 build.py` → `index.html`, `method.html`, `resources.html`, `units/*.html`
- Output is indented by `htmlfmt.py` (stdlib only): block elements on their own lines, inline runs kept verbatim. Every page validates clean at https://validator.w3.org/nu/ — keep it that way.
- Hosting: GitHub Pages from `main` (root). Custom domain: www.lifespent.org (CNAME file; apex redirects via Cloudflare).
- OG image: `og.html` is the source; screenshot it at 1200×630 into `assets/og.png` after changes. `SITE_URL` in build.py sets absolute OG URLs.
