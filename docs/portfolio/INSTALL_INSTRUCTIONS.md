# Add the portfolio materials to the GitHub repository

This package is intended to be extracted at the root of your existing `~/business_api` repository. It contains `docs/portfolio/` with documentation and sanitized screenshots.

## 1. Extract the ZIP

If you downloaded `business_api_portfolio.zip` to your Android Downloads folder, open Termux and run:

```bash
cd ~/business_api
pkg install unzip
unzip -o ~/storage/downloads/business_api_portfolio.zip -d .
```

If the ZIP is in a different folder, change the path to match its actual location. If Termux cannot access Downloads yet, run `termux-setup-storage` and approve the Android permission.

## 2. Review the files

```bash
cd ~/business_api
find docs/portfolio -maxdepth 2 -type f
```

Read the documents and inspect screenshots before pushing. The included screenshots have customer table rows/recent sale details blurred, but review them yourself before making the repository public.

## 3. Add the screenshot gallery to README

Open `README.md` and append the content from `docs/portfolio/README_GALLERY_SECTION.md`. You can use a terminal editor such as `nano README.md`. Keep the gallery image paths relative to the repository root.

## 4. Check and push

```bash
git status -sb
git add README.md docs/portfolio
git diff --cached --check
git diff --cached --stat
```

Make sure the staged files are only the README and intended portfolio files. Then:

```bash
git commit -m "Add portfolio case study and screenshots"
git push origin main
git status -sb
```

The push updates GitHub. Render may run an automatic deployment because the repository changed; these documentation-only changes do not intentionally change application code. Verify Render remains healthy after the push.
