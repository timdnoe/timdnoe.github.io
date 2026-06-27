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

## Publishing

GitHub Pages serves this repo's default branch (`main`) at
`https://timdnoe.github.io/` and, once DNS is configured, at
`https://timothynoe.com/`.
