# timothynoe.com

Personal academic homepage and CV for Timothy Noe, served via GitHub Pages.

## Single source of truth

All CV content lives in **`cv.yml`**. From it, a build step generates two
outputs that stay in sync:

- **`index.html`** — the website.
- **`assets/CV.pdf`** — the downloadable / shareable PDF (linked from the site's
  "Download CV" button).

**You only ever edit `cv.yml`.** Do not edit `index.html` by hand — it is
generated and will be overwritten.

### How it builds

On every push to `main` that touches the content, the **Build CV** GitHub Action
(`.github/workflows/build-cv.yml`) runs `build.py`, regenerates `index.html` and
`assets/CV.pdf`, and commits them back. Nothing to run locally.

To build locally instead:

```bash
pip install -r requirements.txt      # needs WeasyPrint's system libs (pango, etc.)
python build.py
```

## Files

- `cv.yml` — **the only file you edit**: your CV content.
- `build.py` — renders the template + cv.yml into `index.html` and `assets/CV.pdf`.
- `templates/index.html.j2` — page layout (Jinja2).
- `styles.css` — screen styles for the website.
- `print.css` — styles for the PDF and printing.
- `assets/` — generated `CV.pdf`; also drop a `headshot.jpg` here and set
  `basics.photo` in `cv.yml` to show it.
- `CNAME` — custom domain (`timothynoe.com`).
- `tb/` — the **Terebinth Translation** reader (see below).
- `sync_tb.py` — snapshots the TB New Testament from AncientLibrary into `tb/data/`.

## Terebinth Translation reader (`/tb/`)

`https://timothynoe.com/tb/` is a self-contained parallel reader for the
Terebinth Translation (TB) of the New Testament: each verse shown beside the
SBLGNT Greek, with hover/tap word-level morphology.

- **Source of truth:** [AncientLibrary.org](https://ancientlibrary.org). The
  reader serves a *dated snapshot* in `tb/data/` so it loads instantly and never
  depends on the API being up — important for reviewers.
- **Keeping it current:** the **Sync TB** GitHub Action
  (`.github/workflows/sync-tb.yml`) re-runs `sync_tb.py` weekly (and on manual
  dispatch via the Actions tab) to pull the latest Greek + TB + morphology and
  commit any changes. Run `python sync_tb.py` locally to refresh by hand
  (stdlib only — no extra dependencies). Use `--books nt-john` to scope, or
  `--no-words` to skip morphology.
- **No build step:** `tb/index.html`, `tb/reader.css`, and `tb/reader.js` are
  plain static files that fetch the JSON in `tb/data/` (same origin).

## Publishing

GitHub Pages serves this repo's default branch (`main`) at
`https://timdnoe.github.io/` and, once DNS is configured, at
`https://timothynoe.com/`.
