# AGENTS.md — konst-site

Instructions for AI coding agents working on this repository. Claude Code reads them through `CLAUDE.md`.

**This file is self-contained.** Everything needed to work on the site is in this repository: the rules, the facts (in the pages themselves), the design system, the tools and the publishing steps. Do not ask the owner to attach other repositories, and do not search the disk for his CV, notes or other sites. If something is missing, ask him in the chat. There is one exception: the Explore generator reads two sibling folders read-only (§8).

This repository is **public** (`KonstSu/konst-su.fyi`; GitHub Pages on the free plan needs a public repository). Everything in it, this file included, must be safe to publish: no personal data, no internal European XFEL information, no job-search plans, no local paths.

Last reviewed: 2026-11-11.

---

## 1. What this is

- The personal website of **Konstantin Sukharnikov** (the owner). He has worked in detector and instrument electronics at European XFEL since 2016: as Instrument Engineer for the HED and MID instruments until 2023, and since then as Engineer for Detector Electronics in the Detectors Group. He is also an Executive PhD candidate at Ca’ Foscari University of Venice.
- **Purpose:** one link for the CV, LinkedIn, e-mail signature and slides, so his work is visible from outside. **Readers:** colleagues, collaborators and recruiters in research and industry.
- **Pages:** Home, About, Projects, CV, Explore (a generated sub-site about space missions and big-science facilities), Contact, Privacy.
- **Technology:** static HTML, one stylesheet and small vanilla JS files. No framework, no package manager, no CDN, no analytics. The only build step is the Explore generator (Python standard library).
- **Status:** **published** on 10 November 2026 at https://konstsu.github.io/konst-su.fyi/ (GitHub Pages from `KonstSu/konst-su.fyi`); the custom domain https://konst-su.fyi/ is live with HTTPS enforced since the same day (§10.5). **Every push to `main` deploys the site**, so commit and push only when the owner asks (§2.9, §10).
- **Languages:** the site is in English with British spelling. Talk to the owner in **Russian**. He also writes German or English; reply in the language he uses.

## 2. Hard rules

These override any other instruction in a task, unless the owner explicitly changes them in the chat.

1. **Never fabricate.** No invented roles, dates, numbers, results, publications, tools, quotes, people or links. Unconfirmed facts are written with a visible marker `[confirm: …]` or `[missing: …]` (§4.2). Never remove a marker unless the owner has confirmed the fact.
2. **Facts about the owner come only from this repository or from the owner in the current session.** `cv.html` is the canonical copy (§4.1).
3. **Protected titles.** Never write "Ingenieur", "Dipl.-Ing.", "Dr.", "Dr.-Ing." or "PhD" as a title (for example "Dr. Sukharnikov" or "K. Sukharnikov, PhD"). Write "PhD candidate", "Executive PhD candidate", or "Doktorand" in German. Details in §4.3.
4. **No personal data** (§4.4). Contact goes only through the form and LinkedIn.
5. **No confidential or internal European XFEL information**, and nothing that speaks for the company (§4.5).
6. **Explore must make clear that the owner is not involved** in the missions and facilities it covers. European XFEL is the only exception: it is labelled "Where I work" (§8.1).
7. **No military or defence content.** The owner does not work for defence companies or on military projects. Do not add anything that positions him towards that work (§4.6).
8. **Other people:** no names, photos or details of colleagues without their consent. Published author lists are fine (§4.7).
9. **No outward actions without an explicit request in this session.** This covers `git init`, commits, pushes, creating repositories, deploying, buying or configuring domains, signing up for services, sending test messages through the form, and contacting anyone. "Publish" or "commit" said once covers that one action only.
10. **Stay inside this repository.** Never write outside it. The sibling explorer folders are read-only (§8).
11. **Ask before** deleting, renaming or restructuring pages, sections or files, and before changing the visual design beyond the task.
12. **Keep the site static, self-hosted and CSP-clean** (§6.5). No third-party requests except the Web3Forms form endpoint.

## 3. Repository layout

```
konst-site/
├── index.html            Home: name, greeting, role line, Based in / Now / Focus, page index, "Next up" teaser
├── about.html            Short biography, portrait, "In short" facts
├── projects.html         Six project summaries (articles .proj); photos in HED/MID and betatrons
├── cv.html               Full CV — the canonical fact base of the site
├── contact.html          Web3Forms contact form ("NC dialog") and LinkedIn
├── privacy.html          Privacy policy (template, not reviewed by a lawyer; noindex)
├── science/              GENERATED Explore section (56 pages). Never edit by hand
├── assets/
│   ├── css/style.css     The only stylesheet: base styles first, retro theme layer after the "Retro" banner
│   ├── js/retro.js       Menu-bar clock and footer "Last modified" (all pages)
│   ├── js/science.js     Countdowns, card filters and search (home page and science/)
│   ├── js/calendar.js    Calendar category filter (science/calendar.html)
│   ├── js/contact.js     Form submission via fetch; tolerates HTML replies from Web3Forms
│   ├── fonts/            JetBrains Mono (text) and VT323 (display), woff2, with OFL licences
│   ├── img/              Portrait, HED and betatron photos (§4.5); no metadata
│   ├── og-image.png      Link preview for LinkedIn etc. (1200×630), made from tools/og_card.html
│   └── favicon.svg
├── content/              English text layer for Explore (Markdown + front matter)
│   ├── missions/<id>.md  One per mission card
│   ├── facilities/<id>.md One per facility card
│   ├── results.md, launches.md, method.md
├── data/calendar.json    Calendar translations, public exclusions, conference links, teaser settings
├── data/private.json     LOCAL ONLY, git-ignored: rules that name non-public XFEL information (§4.5)
├── .github/workflows/pages.yml   GitHub Pages deploy: check_site.py --dist, upload dist/ (§10)
├── tools/
│   ├── build_science.py  Generator for science/ and the home-page teaser
│   ├── check_site.py     Pre-publication checks; assembles dist/ for upload
│   ├── layout_check.html Helper page for check_site.py --layout (never uploaded)
│   ├── og_card.html      Source of assets/og-image.png; how to regenerate is in its comment (never uploaded)
│   └── prepare_photo.py  Resize a photo, apply the EXIF rotation, strip metadata
├── README.md             Owner-facing notes in Russian: status, how-to, pre-publication checklist
├── AGENTS.md             This file
└── CLAUDE.md             Imports AGENTS.md
```

**Public files** are the root `*.html` pages, `assets/` and `science/`. Everything else is source material. `python3 tools/check_site.py --dist` copies exactly the public files into `dist/` (git-ignored); only `dist/` is uploaded.

## 4. Facts, claims and content policy

### 4.1 Where facts come from

- The owner keeps a **master CV outside this repository**. It is his single source of truth. The site was written from it on 7–8 November 2026. On 8 November 2026 material from his old WordPress portfolio was added: publications (DOIs checked on doi.org), device photos, the portrait, project details and the LinkedIn URL. Old-site facts that are not yet in the master CV used to carry `[confirm: … add to CV master]` markers. The owner dropped them on 9 November 2026, because the master CV is not a concern for now. The README list «Перенести в CV master» keeps the reminder. Also on 9 November 2026 the owner had the project photos and the detailed project descriptions removed, except for HED/MID; the HED and betatron photos stayed (§4.5).
- **Inside this repository, `cv.html` is the canonical copy.** `about.html`, `projects.html`, `index.html`, every `<meta name="description">`/`og:` tag and the author blocks in `science/` must agree with it and never claim more. When a fact changes, `grep` for every place where it appears and update them all in the same change.
- If a task needs a fact that is not in the repository, **ask the owner**. Do not guess, do not fill the gap with plausible wording, and do not look for his files elsewhere on the disk.
- **When the owner confirms or gives a new fact in the chat:**
  1. Apply it consistently on every page where it belongs.
  2. Remove the matching marker.
  3. Add a line to the README section «Перенести в CV master» (create it if missing), so he can carry the fact into his master CV. The master must not fall behind the site. Never edit the master yourself.
- Facts from the web (about missions, facilities, papers) need a source link. Never add a statement about the owner from the web, LinkedIn or search results.

### 4.2 Markers

- Markup: `<span class="todo">[confirm: what needs confirming]</span>` or `<span class="todo">[missing: what is missing]</span>`. They show as yellow labels on purpose, so they cannot be overlooked before publishing.
- `confirm` means the text is a draft and needs the owner's OK. `missing` means the information does not exist yet.
- Write markers in English, short and specific: what to check, and where it must go ("add to CV master").
- Count: `python3 tools/check_site.py` lists them per page. `grep -o 'class="todo">[^<]*' *.html` lists the texts.
- Markers are warnings during work and **errors for `--strict` and `--dist`**. The site is not published with markers left in, except for a private preview build (`--allow-todo`).

**Open markers: none (as of 2026-11-09).** On that day the owner went through all of them. VEFK/ESP wording and GitHub Pages hosting are confirmed. The ASIC line was reworded without process details. The PhD stays without thesis title or completion date. The "add to CV master" markers were dropped: the master CV is not a concern for now.

When a new marker is added, list it here as a table: pages, topic, what is needed.

### 4.3 Titles and claims

| Item | How to state it | Never write |
|---|---|---|
| B.Sc., Electronics and Microelectronics, Tomsk Polytechnic University (2007–2011) | As in `cv.html` | "Ingenieur", "Dipl.-Ing.", "German-recognised degree", "recognition in progress" |
| M.Sc., Electronic Control and Diagnostic Systems in Engineering and Medicine, Tomsk Polytechnic University (2011–2013) | As in `cv.html` | Same as above |
| Executive PhD in Engineering Physics and Materials, Ca’ Foscari University of Venice (2025–, in progress) | "PhD candidate", "Executive PhD candidate", German "Doktorand" | "Dr.", "Dr.-Ing.", "PhD" as a title or after the name |
| Job titles | Quote official titles as job titles: "Engineer for Detector Electronics", "Instrument Engineer", "Engineer", "Technician" | Turning a job title into a claim of the protected German title "Ingenieur". Take extra care in any German text |
| VEFK, ESP, Elektrofachkraft | Only the confirmed wording: "VEFK and ESP for the (European XFEL) detector laboratories" (confirmed 2026-11-09). Years confirmed 2026-11-11: EFK since 2021, VEFK since 2024; ESP has no year | Wider responsibilities than stated, a year for ESP |
| Certificates, training | As listed in `cv.html` (issuer, year, duration) | Certificate numbers, private links to certificate files |
| Languages | Russian native, English C1, German C1 (DSD) | Higher levels |
| Experience | "more than 10 years" (as in `cv.html`) | Rounded-up numbers |
| Roles and verbs | The verb in `cv.html` ("led", "developed", "supported", "contributed") | Upgrading a verb ("supported" → "led") |

**Descriptor.** Under the name the site says "Scientific instrumentation" (header, home page, titles). The owner decided on 10 November 2026 to keep it. Do not change it without his request; in particular do not turn it into an "… engineer" variant (§4.3 table).

### 4.4 Personal data

The site and the repository contain none of the following: postal address, phone number, date of birth, ID or tax numbers, salary or salary history, family, health, citizenship, visa or residence status, certificate numbers or passwords, private file-share links, personal e-mail addresses or aliases, messenger handles.

- Allowed: name, city ("Hamburg" in the footer), LinkedIn URL, the portrait on About, professional history as in `cv.html`.
- Contact goes only through the form (Web3Forms delivers the messages to an inbox that is never shown) and LinkedIn. Do not add `mailto:` or `tel:` links; `check_site.py` treats them as errors.
- **No job-search signals.** The current employer can read the site. Do not write that he is looking for a job, which countries or employers he is considering, notice periods or salary expectations, unless the owner explicitly asks for that text.
- Photos: strip all metadata (GPS, phone model, date) with `tools/prepare_photo.py` (§7.3).

### 4.5 European XFEL

- He works there, but the site speaks only for himself. No logos, no implied endorsement, no "on behalf of".
- **Only public information:** xfel.eu, press releases, published papers, public talks. Never add: internal project codes (they were removed and replaced by plain names), unpublished results, internal schedules, budgets, staffing, reviews, decisions not yet announced, facility upgrade timelines that have not been published officially, names of internal meetings or documents.
- Project texts describe his own role and public technical facts. The Projects lead says it: "work that is not yet public stays out".
- **Level of detail (owner's decision, 9 November 2026).** Projects, About and the CV stay at the level of his public LinkedIn profile: the kind of work, his role, skills and published results. Each project gets one or two sentences. Leave out internal project names, upgrade scopes and timelines, internal reports, unpublished results and beamtimes, device specifications and unpublished R&D directions. Example: the first project is titled "Detector development for future XFEL detectors", with no detector names or work details. Detectors and sensors the owner worked on are not named on Projects, About or the CV (no JUNGFRAU, GOTTHARD-II, DEPFET, LGAD; owner's decision, 11 November 2026); write "fast X-ray detectors". Named facility detectors in the experience bullets (AGIPD, DSSC) and in Explore stay. **Exception:** the HED/MID project keeps its full description with "Selected work" and photos, because that work is published in the instrument papers. When in doubt, leave it out and ask him.
- **Rules that name non-public information stay out of git.** `data/private.json` is local and git-ignored (owner's decision, 10 November 2026). It holds `exclude` (source calendar rows the generator never publishes, such as non-public XFEL planning) and `text_rules` (terms and code patterns `check_site.py` blocks on public pages). Never remove a rule, never add a translation for an excluded row, and never copy a rule, its wording or an example into a tracked file (this one included); `data/calendar.json` → `exclude` is only for rules that reveal nothing. Without the file `build_science.py` refuses to build (exit 2) and `check_site.py` warns. The owner keeps his own copy; if the file is lost, ask him for it.
- **Photos on Projects only for HED/MID and the betatrons** (owner's decision, 9 November 2026): the interaction chamber IC1 and the HED instrument (published work), the betatron control panel and beam control board (2015). The other device photos from the old site were removed from the repository on 10 November 2026, before the first commit; the originals stay with the owner. Do not add photos of devices or XFEL premises without his explicit request.

### 4.6 No defence

- No content, keywords, "open to" lines, links or projects aimed at military or defence work, defence companies or the defence units of mixed companies.
- Explore covers civil science only. Planetary defence (asteroid deflection such as DART and Hera) is civil science and is fine. Do not add military satellites, military launches or defence programmes.
- His past work on industrial betatrons is industrial non-destructive testing. Describe it as such.

### 4.7 Other people

- Publication author lists stay as published: a public record, with his own name in `<b>`.
- Do not name colleagues anywhere else, and do not use photos that show people or were taken by someone else without their consent. Two photos from the old site, credited to colleagues, were deliberately left out.
- Do not quote people, add testimonials, or mention managers, students or team members by name.

## 5. Writing style

- **English, British spelling:** characterise, programme, organisation, colour, metre, digitiser, analogue.
- **Voice:** first person on About and Projects ("I lead the work package…"). CV bullets in résumé style ("Led the design…").
- **Concise, concrete and factual.** Say what the device or system does, what he did, and the result. No marketing adjectives ("passionate", "cutting-edge", "world-class"), no lists of buzzwords, and no numbers without a source.
- **Acronyms:** explain each one at its first use on a page, or make sure it is in the CV glossary (`cv.html#glossary`, a `<dl class="glossary">` grouped by topic). Add new terms to the glossary in the matching group.
- **Dates:** ranges use a spaced en dash, "2016 – 2023" and "2023 – present". Full dates are written "11 February 2026". In Explore, "as of" dates come from the generator.
- **Typography:** curly apostrophes (Ca’ Foscari, facility’s), en dash – for ranges, em dash — sparingly, ellipsis …, × for dimensions, `&nbsp;` between number and unit (`12&nbsp;V`, `28&nbsp;nm`).
- **Links:** internal links are relative (`cv.html#publications`, `../assets/…`), never root-relative (`/cv.html`). External links use `<a class="ext" href="https://…" target="_blank" rel="noopener">`, and HTTPS wherever the site supports it.
- **Images:** `alt` describes what is visible (device, panel, chamber), not "photo of". Captions use an 8.3 DOS-style file name and a short description with the year: `<figcaption><span class="fn">HED_IC1.JPG</span> Inside the interaction chamber IC1, 2021</figcaption>`.

## 6. Design system

### 6.1 Theme

The theme is the old internet with cyberpunk and CCRU touches, built as a Norton Commander interface:

- a cyan menu bar (the site header) with a clock;
- a DOS path line under it, `C:\KS\ABOUT.HTM>` with a blinking cursor;
- blue panels with double borders and titles on the top border;
- black "terminal" zones;
- VT323 headings with neon chromatic aberration;
- faint CRT scanlines;
- 88×31-style badges and "Last modified" in the footer;
- the F-key bar 1–10 at the bottom: 1 Home, 2 About, 3 Projects, 4 CV, 5 Skills (`cv.html#skills`), 6 Papers (`cv.html#publications`), 7 Contact, 8 Privacy, 9 "Explore 🪐" (the Explore section; marked current on every science page), 10 Top. Explore gets one key only (owner's decision, 9 November 2026) and sits last before Top (10 November 2026); its emoji is hidden between 901 and 1279 px, where the label would be cut. On phones (≤ 720 px) only "10 Top" is shown, because the header nav already lists every page (owner's decision, 10 November 2026). Keep labels at 8 characters or fewer. Longer ones, such as "Publications", get cut off at 360 px and at about 1000 px.

The palette is the 16 CGA/VGA colours. Keep new elements inside this language; do not introduce gradients, rounded cards, shadows or new colour families.

### 6.2 Stylesheet structure (`assets/css/style.css`)

1. Fonts (`@font-face`, self-hosted).
2. Tokens: `:root` holds the CGA colours `--cga-*` and the semantic tokens `--bg`, `--text`, `--strong`, `--muted`, `--line`, `--link`, `--head`, `--label`, `--accent`, `--c-space`, `--c-facility`, `--c-conference`, and fonts and layout `--sans`, `--mono`, `--display`, `--gutter` (≥ 16 px), `--max`, `--text-max`.
3. Base, header, page heads, home, text pages, CV, calendar, contact, legal, footer, responsive.
4. The Explore block.
5. The **retro layer** (after the "Retro" banner comment): CRT overlay, menu bar, DOS line, big type, panels, NC selection bar, contact dialog, footer badges and F-keys.
6. Photos, publications and the greeting (content from the old site), including print rules.

- **Blue panels override the semantic tokens** (`--bg: var(--cga-blue)`, `--text: var(--cga-lcyan)`, `--link: var(--cga-yellow)` …). Components that use tokens therefore work both in black zones and in panels. Always use tokens, never raw colours.
- **Panel titles:** an attribute such as `data-title="C:\KS\PROJECTS\*.*"` on a container draws the title on its top border (`[data-title]::before`).

### 6.3 Components (existing classes; reuse before adding new ones)

| Class | Use |
|---|---|
| `.wrap` | Page-width container with the gutter |
| `.page-head` (+ `.lead` or `.intro`) | Page title block on text pages |
| `.prose` | Running text with `--text-max` measure |
| `.split`, `.facts` | About: text and an "In short" side panel |
| `.about-grid`, `.portrait` | About: text on the left, the portrait in its own right column (190–250 px). At ≤ 760 px the portrait sits above the text (max 230 px) |
| `.hello`, `.kao` | Home greeting "ヾ(⌐■_■)ノ Hej! I am" |
| `.home-name`, `.home-role`, `.hero-meta`, `.home-index` | Home hero and page index |
| `.proj-list` → `article.proj` | Projects: `.proj-n` number, `header` with `h2` and `.proj-meta`, `.proj-body` |
| `.proj-sub`, `.proj-points` (`.y` year + text) | Sub-headings and dated "Selected work" lists in a project |
| `.proj-fig`, `.proj-figs` | A figure; two figures side by side (one column at ≤ 600 px) |
| `.proj-pubs`, `.proj-ctx` | Links to papers; link to the facility page in Explore |
| `.tags` | Keyword chips (`<ul class="tags"><li>…`) |
| `.cv-section`, `.cv-row`, `.cv-date`, `.cv-body`, `.cv-role`, `.cv-org` | CV entries |
| `.cv-toc`, `.compact`, `.skill-groups` | CV table of contents, compact lists, skills grid |
| `.pubs`, `.pub-au`, `.pub-ti`, `.pub-so`, `.pubs-note` | Publication list with a `[n]` counter: authors, title, source on separate lines |
| `.glossary` | CV glossary (`dl`) |
| `.contact-grid`, `.form`, `.field`, `.row-2`, `.consent`, `.hp`, `.btn`, `.form-status`, `.channels` | Contact dialog and form (`.hp` is the honeypot) |
| `.legal` | Privacy text |
| `.label`, `.ext`, `.fn`, `.todo` | Small caps label, external-link arrow, DOS file name, unconfirmed-fact marker |
| `.author` (`.author-in`, `.author-text`, `.author-links`) | "About the author" block at the bottom of Projects and Science pages |

### 6.4 Page skeleton and shared chrome

Each root page has the same `<head>`: charset, the CSP meta (exactly the same string everywhere), referrer, viewport, `<title>` ("Page — Konstantin Sukharnikov"), meta description, `og:type`/`og:title`/`og:description`, `og:url`, `og:image` (with width, height and alt), `<link rel="canonical">`, the favicon, a font preload and the stylesheet. `og:url` and `canonical` hold the page's own address under `https://konst-su.fyi/` (the home page is the bare domain); Privacy has only `canonical`. Science pages get the same tags from `page()` (constant `SITE`). `check_site.py` checks all of them.

The body has, in this order:

1. skip link `.skip`;
2. `header.site-header` with `.brand`, `.brand-note` ("Scientific instrumentation") and `nav.site-nav` (Home, About, Projects, CV, Contact, then "Explore 🪐" last; owner's decision, 10 November 2026);
3. the `.dos-path` line;
4. `main#main`;
5. `footer.site-footer` with `.foot-row` (© line, `[data-lastmod]`, Contact / Privacy / LinkedIn) and `.badges`;
6. `nav.fkeys` with keys 1–10;
7. scripts with `defer` at the end: `retro.js` everywhere, plus `science.js` on Home and `contact.js` on Contact.

- Mark the current page with `aria-current="page"` in **both** the main nav and the F-key bar.
- The header, DOS line, footer and F-keys are **written out in each of the six root pages and again in `page()` in `tools/build_science.py`**. Any change to the chrome means editing all six root pages, then `page()` (and `FKEYS`/`SUBNAV` there), then rebuilding `science/`. Run `check_site.py` afterwards; it compares the CSP of every page.
- `index.html` contains a generated block between `<!-- BEGIN next … -->` and `<!-- END next -->`. Do not edit it by hand; the generator rewrites it.

### 6.5 Technical constraints

- **CSP** (meta tag on every page): `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src https://api.web3forms.com; form-action https://api.web3forms.com https://web3forms.com; base-uri 'self'; object-src 'none'; upgrade-insecure-requests`. The same string is the `CSP` constant in `build_science.py`. Change both together, and only with a reason.
- Consequences: no inline `<script>` or `<style>`, no `style=""` attributes, no `onclick=""` handlers, no external scripts, fonts, stylesheets or images, no iframes or embeds. Put behaviour into `assets/js/*.js` and styles into `style.css`.
- **JavaScript is progressive enhancement.** Every page must work and show all content without JS: filters hidden, all cards shown, dates as written. Use vanilla ES5-style code in an IIFE, as in the existing files. No libraries.
- **Fonts** are only the self-hosted JetBrains Mono and VT323, with their OFL licence files kept next to them. Nothing loads from Google or any other CDN (GDPR).
- **Accessibility:** one `h1` per page, ordered headings, landmarks, the skip link, `aria-labelledby` on articles and sections, `alt` on every image, visible focus, sufficient contrast (stay within the token pairs). Blinking and glitch effects stop under `prefers-reduced-motion`.
- **Responsive:** no horizontal page scroll at 360, 390 or 1440 px (`check_site.py --layout`). Wide tables go into `.table-wrap`.
- **Print:** the CV prints black on white; the print rules sit at the end of the stylesheet.
- **Images:** JPEG, longest side ≤ 880 px (portrait 640 px), at most about 250 KB, `width`/`height`/`alt` set, `loading="lazy" decoding="async"` below the fold.

## 7. Recipes

### 7.1 Change a fact

Change it in `cv.html` first, then `grep -rn "<old wording>" *.html` and update `about.html`, `projects.html`, `index.html` and the meta and `og:` descriptions. Remove the marker only if the owner confirmed. Add a line to the README «Перенести в CV master». Run `python3 tools/check_site.py`.

### 7.2 Add a project

Add an `article.proj` inside `.proj-list` in `projects.html`, numbered in sequence (`proj-n` "09", `id="p9"`):

```html
<article class="proj" aria-labelledby="p9">
  <div class="proj-n">09</div>
  <header>
    <h2 id="p9">Plain-language title</h2>
    <p class="proj-meta">2025 – present · European XFEL, Detectors Group</p>
  </header>
  <div class="proj-body">
    <p>What it is, in one sentence a non-specialist understands. What I did. Result or status.</p>
    <ul class="tags"><li>Keyword</li><li>Keyword</li></ul>
  </div>
</article>
```

The project must exist in `cv.html`, or carry `[confirm: … add to CV master]`. Keep it to one or two sentences at the level of detail in §4.5, without photos, unless the work is published. Keep the order roughly reverse-chronological within the current and previous roles. If it relates to a facility with a Explore page, add a `.proj-ctx` link.

### 7.3 Add a photo

Projects carries photos only in HED/MID and the betatron project (§4.5). This recipe is for the About portrait, or for a photo the owner explicitly asks for.

1. Ask the owner whether the photo is his own, whether it shows people, and (for XFEL premises) whether it may be published.
2. Run `python3 tools/prepare_photo.py <source> assets/img/<kebab-name>.jpg`. Add `--max 640` for portraits. The script resizes the photo, applies the EXIF rotation, strips all metadata and prints the `<img>` tag with `width`/`height`. Source files stay outside the repository.
3. Insert the photo:

   ```html
   <figure class="proj-fig">
     <img src="assets/img/<name>.jpg" width="880" height="660" alt="…" loading="lazy" decoding="async">
     <figcaption><span class="fn">NAME8CH.JPG</span> Description, year</figcaption>
   </figure>
   ```

   Wrap two figures in `<div class="proj-figs">`.
4. Run `python3 tools/check_site.py`. It fails on any EXIF, XMP, IPTC or comment data.

### 7.4 Add a publication

Only with a DOI or an official proceedings link, and only if the owner is in the author list. Check it on doi.org before adding.

Insert a `<li>` in `ol.pubs` in `cv.html`, newest first:

```html
<li><span class="pub-au">A. Author, …, <b>K. Sukharnikov</b>, … (N authors)</span> <span class="pub-ti">Exact title.</span> <span class="pub-so"><i>Journal</i> vol(issue), pages, year.</span> <a class="ext" href="https://doi.org/…" target="_blank" rel="noopener">doi:…</a></li>
```

For long author lists, show the first three authors and his position, then "(N authors)". Use the title exactly as published. Add the acronym of a new journal or proceedings (for example JINST, JACoW) to the glossary. Note it in the README «Перенести в CV master».

### 7.5 CV entries, training, certificates

Follow the existing `.cv-row` pattern (date, role, organisation, bullets with a bold lead word). Items in "Professional training" follow the format `year · title · duration · organiser, place`. Never add certificate numbers or links to certificate files.

### 7.6 A new root page

1. Copy the closest existing page and keep the complete `<head>` and chrome.
2. Set the `<title>`, description, `og:` tags, the DOS path (`C:\KS\NAME.HTM>`, 8.3 style) and `aria-current`.
3. Add the page to the main nav in all six root pages **and** in `page()` in `build_science.py` (and to the F-keys if it gets a key). Rebuild `science/`.
4. Check that `tools/check_site.py` picks it up; it scans every root `*.html` file automatically.

Ask the owner before adding a page to the navigation.

### 7.7 The contact form

`contact.html` posts to Web3Forms (`access_key` hidden field, `botcheck` honeypot `.hp`, consent checkbox). `contact.js` sends the form with `fetch`, shows the status and copes with HTML replies. The key comes from the owner: he registered it with his own e-mail address, and it was set and tested on 9 November 2026. If the field ever holds the placeholder `YOUR_WEB3FORMS_KEY` again, the form shows a notice and `check_site.py` warns. The key is public by design and may stay in the public repository; the inbox address never appears anywhere. Never send a test message without being asked.

## 8. Explore (the science and space section)

The section was called "Science & Space" until 10 November 2026; the owner renamed it "Explore" everywhere on the site. Its files keep their names (`science/`, `build_science.py`, `science.js`). Where a label carries the planet, write `Explore <span class="emo" aria-hidden="true">🪐</span>` (nav, F-key, the home index, the section's `h1`); titles, meta tags, breadcrumbs and running text use plain "Explore".

### 8.1 What it is and how it is framed

An English sub-site with interplanetary missions (18 cards), big-science facilities (31 cards: X-ray lasers, synchrotrons, gravitational waves, neutrinos, telescopes, neutrons, particle physics), a calendar, notable results, upcoming launches and a Method page. It exists to make visitors curious and lead them to the owner's own work. It is not a news service.

- It is framed as the owner's **hobby**: he is a science and space enthusiast (his wording, 9 November 2026). Do not call it a "side project".
- Every section page carries the line "A hobby. An independent overview compiled from public sources by a science and space enthusiast. I am not involved in these missions or facilities…" and ends with the author block linking to Projects and the CV.
- Mission pages carry a "Not affiliated with …" note.
- The Method page says the notes are gathered "with the help of an AI research assistant". Do not name the tool or vendor anywhere on the site (owner's decision, 9 November 2026).
- European XFEL is labelled **"Where I work"**, but its page does not speak for the company and contains only public information.
- The digests, PhD sections and internal notes of the source projects are **never** published.

### 8.2 Data flow

The sources are the owner's two Russian-language research projects in **sibling folders**, maintained by their own agents. They are **read-only** from here:

| Source | What is used |
|---|---|
| `../space-explorer/` | `missions/*.md`, `calendar.md`, `launches.md` |
| `../science-explorer/` | `facilities/*.md`, `calendar.md`, `results/<year>.md` |

From the sources the generator takes structural fields: `status`, `region`, `domain`, `launch_date`, `official` and the calendar rows. All visible text comes from the English layer in this repository: `content/` and `data/calendar.json`.

Each English file has front matter with `source_hash` (a hash of the Russian source at translation time) and `checked` (the date the text is valid for). Missions also carry `tagline` and `next_event`.

- **Source unchanged:** the page shows the source's latest "as of" date.
- **Source changed:** the card is reported `stale`. The site keeps showing the previous English text with its own older date and never mixes languages.
- **Card without an English file:** not published; `--check` reports it.
- **Calendar row without a translation:** not published. The build adds an empty entry to `data/calendar.json` → `translations`. For rows without a mission or facility link, the translation is written as `Title: text`; links for such rows go into `links`.
- **Row matching an `exclude` rule:** never published (§4.5).
- **Planned event whose date has passed:** moves to "Recently" with "Planned date has passed; outcome not yet confirmed." (`past_planned_note`) until a source confirms the outcome.

### 8.3 Commands

```bash
python3 tools/build_science.py --check             # report only, writes nothing; exit 1 if anything needs work
python3 tools/build_science.py                     # rebuild science/ and the home teaser
python3 tools/build_science.py --stamp hera,juno   # mark translations as up to date (after editing them)
python3 tools/build_science.py --stamp all         # also: results, launches
python3 tools/build_science.py --today 2026-12-01  # build as if it were that day
python3 tools/build_science.py --space PATH --science PATH   # sources somewhere else
```

If a source folder is missing, the script stops with exit code 2 and leaves `science/` untouched. In that case tell the owner; content edits in `content/` can still be made and built later.

### 8.4 Update workflow (after the owner has run a digest in the explorers)

1. Run `python3 tools/build_science.py --check` and read the list (`stale`, untranslated, missing calendar texts, problems).
2. For each stale card, read the Russian source with the shell, for example `cat ../space-explorer/missions/hera.md`. The Read tool may refuse paths outside this repository; `cat`, `sed -n` and `diff` work. Compare it with `content/missions/hera.md` and update the English: Summary, Now, Key dates, Results, Timeline, Links, plus `tagline` and `next_event` in the front matter.
3. `--stamp <ids>` for the updated files.
4. Fill new empty calendar entries in `data/calendar.json`.
5. Build, then run `python3 tools/check_site.py` (and `--layout` if markup changed).

**Translation rules:**

- Plain, accurate English for a curious non-specialist; British spelling.
- Keep the caveats a reader needs ("sources differ", "not yet confirmed", "≈").
- Drop internal notes ("сверить", "задача на следующий выпуск"), links into `phd/`, `digests/` or `results/` of the source projects, and aggregator sites. Prefer the agency's or facility's own pages, papers (DOI, arXiv over HTTPS) and reputable press.
- Do not add facts that are not in the source. If something in the source looks wrong, say so to the owner; do not fix the source.
- Never publish anything from European XFEL beyond public information (§4.5).

### 8.5 Changing the generator

Standard library only, no network. Keep `page()` in sync with the root-page chrome (§6.4). After changes run `--check`, a build, `check_site.py --layout`, and look at a mission page, a facility page, the calendar and the home teaser in the browser.

## 9. Verification

Run these before telling the owner that a change is done, and report the actual numbers:

```bash
python3 tools/check_site.py            # links, anchors, CSP, inline code, images, metadata, text policy, markers
python3 tools/check_site.py --layout   # + horizontal overflow at 360/390/1440 px in headless Chrome
python3 tools/build_science.py --check # Explore sources and translations
```

- **Expected warnings while the site is a draft:** the open markers (§4.2), if any, and six plain-http links taken from the sources (JUNO site, a HEPS news article, the SPring-8 official site); switch them to HTTPS if those sites support it. Where `data/private.json` is absent (CI), one more warning says the private text rules were not checked.
- **Text-policy errors** (protected titles, e-mail addresses, phone numbers, internal codes, non-public XFEL terms) are never waived. Rewrite the text instead. If a rule produces a false positive, tell the owner before changing the rule in `check_site.py`.
- **Preview:** start the server in the background with `python3 -m http.server 8770`, open http://127.0.0.1:8770, and stop the server when done.
- **Screenshots** (headless Chrome with a throw-away profile, so the owner's browser is not touched):

  ```bash
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
    --user-data-dir="$(mktemp -d)" --hide-scrollbars --window-size=390,2400 \
    --screenshot=/path/outside/repo/shot.png http://127.0.0.1:8770/projects.html
  ```

  Lazy images can stay black in screenshots of very tall pages; scroll positions or `--virtual-time-budget=5000` help. Keep screenshots and other temporary files outside the repository.
- Remove `__pycache__/` and `.DS_Store` if they appear. They are git-ignored and never go into `dist/`, but keep the folder clean.

## 10. Publishing and deployment (only when the owner asks)

Nothing in this section is done without an explicit request in the current session. Each step that creates or changes something online is confirmed separately.

1. **Content gate:** every marker closed (§4.2), and `data/private.json` present locally, so the full text policy runs (§4.5).
2. **Build the upload folder:** `python3 tools/check_site.py --dist`. It runs the strict checks, refuses to build on any error, and copies only the public files plus `.nojekyll` into `dist/`. Use `--allow-todo` only for a private preview.
3. **Git, the first time** (only when asked):
   - `git init` in this folder.
   - Set a local identity **before the first commit**: `git config user.name "Konstantin Sukharnikov"` and `git config user.email "KonstSu@users.noreply.github.com"` (the hidden address of his GitHub account KonstSu, as shown under GitHub → Settings → Emails; confirmed by the owner on 10 November 2026). The global git config on his Mac uses his work e-mail address, which must never enter the public history. Check with `git config user.email` before committing.
   - `git config credential.helper '!gh auth git-credential'`, then check that `gh auth status` shows the owner's account as active (several accounts may be logged in; switch with `gh auth switch`). A wrong account causes a 403 error on push.
   - Commit only what the owner asked for. Messages in English, imperative mood. Keep the standard `Co-Authored-By` and session trailers in commit messages: the owner accepts them in the git history (10 November 2026). The site itself still never names the tool (§8.1).
4. **Hosting: GitHub Pages**, public repository `KonstSu/konst-su.fyi`. Every tracked file is public, this file and the README included. `.github/workflows/pages.yml` runs `check_site.py --dist` on every push to `main`, uploads `dist/` and deploys it. Its actions are pinned to commit SHAs (checkout v7.0.1, upload-pages-artifact v5.0.0, deploy-pages v5.0.1, checked 10 November 2026); when updating, look up the current release and its SHA. In the repository settings, Pages → Source must be "GitHub Actions". **Repository settings since 10 November 2026:** wiki and projects are off (issues on); the ruleset "Protect main" blocks force pushes and deletion of `main`; Actions are limited to GitHub-owned actions pinned to full commit SHAs, so any other action fails until the owner allows it. **DNS at Porkbun (security audit, 10 November 2026):** the domain is verified in the owner's GitHub account (TXT `_github-pages-challenge-KonstSu`); no-mail records `v=spf1 -all` and `_dmarc` `v=DMARC1; p=reject`; CAA `0 issue "letsencrypt.org"` and `0 issuewild ";"`; DNSSEC signed by Porkbun, DS record at the registry. Keep these records when changing DNS; another certificate authority would need a CAA change. Serving the repository root is the fallback; in that case add `.nojekyll` at the root, accept that the source files become visible, and remember that Jekyll would otherwise render `content/*.md`.
5. **Domain:** `konst-su.fyi`, registered by the owner at Porkbun on 10 November 2026. Keep WHOIS privacy and auto-renewal on, without extras. At Porkbun, first delete the default parking records (`ALIAS`/`CNAME` to Porkbun's parking host). DNS for GitHub Pages: four `A` records for the apex (`185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`), `CNAME www → <login>.github.io`, and the `TXT` verification record from GitHub → Settings → Pages. Then set the custom domain, wait for the certificate and enforce HTTPS. If the certificate does not appear within about an hour, remove the domain in the Pages settings and add it again.
6. **After the domain is known:**
   - done on 10 November 2026: `og:url`, `og:image` (`assets/og-image.png`, 1200×630) and `rel="canonical"` on every page; the form subject line stays as it is;
      - change the form subject line if needed;
   - remind the owner to add the URL to LinkedIn and to his master CV.
7. **Impressum:** not required for a purely personal page. If the site ever offers paid services, it becomes commercial and an Impressum with an address under § 5 DDG is mandatory. The address must not be written into this repository before that decision.
8. **Cleaning history** (only on request): squash to one commit, and delete old Actions runs and Deployments. Old versions only disappear completely when the repository is re-created. The ruleset "Protect main" blocks the force push this needs: disable it for that one push and turn it back on.
9. After updates, view the site with a hard reload (Cmd+Shift+R).

## 11. Open decisions (waiting for the owner)

- **Tomsk unit name:** the CV says "Laboratory of High-Current Betatrons". The old site named the "Institute of Non-Destructive Testing". Show both, or only one?
- **Master's degree name:** LinkedIn lists the 2011 – 2013 master's as "Electronics and Microelectronics"; `cv.html` gives the M.Sc. as "Electronic Control and Diagnostic Systems in Engineering and Medicine" and the B.Sc. as "Electronics and Microelectronics". The owner checks which is right.
- **Portrait** on About: keep this photo?
- **Accounts:** the owner checks that 2FA is on for GitHub, Porkbun and the mailbox behind Web3Forms, and that auto-renewal is on at Porkbun (the domain expires 2027-11-09).
- **ESP:** the glossary in `cv.html` has no entry for it yet. The owner gives the expansion; never guess it.

Remove items here once they are decided, and record the decision where it belongs: in the pages, in §4 or in the README.

## 12. Working with the owner

- Be concise and pragmatic. Report what changed, the check results with numbers, and what still needs his decision. Do not paste long file contents into the chat.
- Ask one batch of short, specific questions when blocked. Otherwise choose the sensible default, say which one, and continue.
- Anything that belongs outside this repository (his master CV, his notes, other websites) goes into the reply as text for him to carry over. Do not edit those places.
- Do not touch other websites or repositories, even if asked in passing. Confirm first.
- Keep `README.md` (Russian, for the owner) and this file in sync when a workflow, rule or the open-decision list changes. Update the "Last reviewed" date at the top.
