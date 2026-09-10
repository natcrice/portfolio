# Natalie Rice — Engineering Portfolio

A static, no-build portfolio site. Plain HTML, CSS, and a tiny bit of
JavaScript. Nothing to install, nothing to compile — open `index.html` in a
browser and it works.

```
portfolio/
├── index.html                 # the whole main page
├── 404.html                   # shown for bad URLs (host-dependent)
├── css/
│   ├── style.css              # site styles + color tokens
│   └── project.css            # extra styles for case-study pages
├── js/
│   └── main.js                # year, mobile nav, project filter, scroll reveal
├── projects/
│   └── example-project.html   # the RC-car case study — copy this per project
└── assets/
    ├── images/                # photos / renders go here
    └── resume.pdf             # drop the résumé here (this exact filename)
```

## 1. Still to do

- **Add `assets/resume.pdf`** — the "Résumé" links 404 until it's there.
- **Add `assets/images/headshot.jpg`** — a portrait crop, ~4:5 ratio, ~600×750 px.
  Then in `index.html` swap the `<svg class="about__photo">` placeholder for the
  commented-out `<img class="about__photo" ...>` line right above it.
- **Fix the LinkedIn URL** — `index.html` and `projects/example-project.html`
  currently point at `https://www.linkedin.com/in/natalie-rice`; change it to
  the real profile URL.
- **Replace the placeholder SVGs** with real project images (see §2).
- **Fill the bracketed `[values]`** in `projects/example-project.html` with
  measured numbers from the RC-car project.

### Colors

Every color is a CSS variable at the top of `css/style.css` (`:root`).
`--accent` / `--accent-link` are the Apple blue; `--orange` is the eyebrow
accent. The site is locked to light mode; a dark palette exists under
`:root[data-theme="dark"]` and turns on only if you add `data-theme="dark"`
to the `<html>` tag.

## 2. Add a project

1. Copy `projects/example-project.html` to `projects/my-thing.html`.
2. Fill in the case study. Keep the structure: problem → approach → results →
   reflection. Put real numbers in.
3. In `index.html`, copy one `<li class="project">…</li>` block, point its
   link at `projects/my-thing.html`, update the title/description, and set
   `data-tags="design analysis prototyping test"` (any subset) so the filter
   buttons work.
4. Replace the inline `<svg class="project__placeholder">` with a real image:
   ```html
   <img src="assets/images/my-thing.jpg" alt="Short description of the image">
   ```
   Aim for ~1200 px wide, compressed JPG/WebP under ~300 KB each.

## 3. Preview locally

Just double-click `index.html`. Or, for cleaner URLs while editing, run a
local server from this folder — whichever you have:

```
npx serve            # Node
python -m http.server 8000   # Python
```

then open the URL it prints (e.g. <http://localhost:3000> or `:8000`).

## 4. Put it online (free)

You don't need the domain yet — deploy first, add the domain later.

### Option A — Netlify drop (easiest)

1. Go to <https://app.netlify.com/drop>.
2. Drag this whole `portfolio` folder onto the page.
3. You get a live URL in seconds (e.g. `random-name.netlify.app`).
4. To update: drag the folder again, or connect a Git repo for auto-deploys.

### Option B — Vercel

1. Push this folder to a GitHub repo (see below).
2. Import the repo at <https://vercel.com/new>. Framework preset: **Other**.
   No build command, output directory `.`.

### Option C — GitHub Pages

1. Create a repo and push (commands below).
2. Repo **Settings → Pages → Build from branch → `main` / root**.
3. Site publishes at `https://<username>.github.io/<repo>/`.
   For a bare `https://<username>.github.io/`, name the repo
   `<username>.github.io`.

```bash
cd portfolio
git init
git add .
git commit -m "Initial portfolio"
git branch -M main
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main
```

## 5. Buy the .com and connect it

1. Register the name at any registrar — Cloudflare Registrar (at-cost),
   Namecheap, Porkbun are all fine. Expect ~$10–15/year.
2. In your host's dashboard, add the custom domain:
   - **Netlify:** Site settings → Domain management → Add domain.
   - **Vercel:** Project → Settings → Domains → Add.
   - **GitHub Pages:** Settings → Pages → Custom domain (this writes a
     `CNAME` file into the repo — keep it).
3. At the registrar, point DNS as the host instructs — usually:
   - `A` / `ALIAS` record for the apex (`yourdomain.com`)
   - `CNAME` for `www` → your host's target
4. Enable HTTPS (one checkbox on all three hosts). DNS can take up to a
   few hours to propagate.

## Notes

- No analytics or trackers are included. If you want privacy-friendly stats,
  add a Plausible or GoatCounter snippet before `</body>` in `index.html`.
- Add `assets/og-image.png` (1200×630) and uncomment the `og:image` line in
  `index.html` for nicer link previews.
