# compress-code

Compress-code is a **proposal generator** for semantic-preserving structural compression.
The **CLI is the real engine**. The web app is a static, GitHub Pages–hosted **demo and explanation layer only**.

## What this is
- A conservative tool that **suggests** compression candidates
- A workflow where **Codex explores** and **humans decide**
- Output is proposals only — **no automatic refactoring**

## What this is not
- Not gambling-style brute force search
- Not intuition-only refactoring
- Not a browser-based execution engine
- Not minification or performance tuning

## CLI usage
```
python compress-code.py <file> [--mode safe|aggressive] [--explain] [--diff]
                         [--min-confidence 60] [--max-proposals 5] [--sort impact|confidence]
```

## Repository layout
```
compress-code/
├─ docs/                (GitHub Pages root)
│  ├─ index.html
│  ├─ app.js
│  └─ style.css
├─ compress-code.py     (CLI prototype)
├─ README.md
└─ LICENSE
```

## Web demo
The GitHub Pages demo **does not execute code**. It only shows a mock/example output to illustrate the workflow.
All real processing happens in the CLI (`compress-code.py`).

## Note on GitHub Pages
Set Pages to deploy from **/docs** (Settings → Pages → Branch: main / Folder: /docs).
