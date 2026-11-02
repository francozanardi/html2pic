# Visual tests (browser references)

These tests render small HTML/CSS cases with html2pic and compare the result pixel by pixel
with what a real browser (Chromium) renders for the same case. They are the main safety net
for rendering behaviour: if html2pic draws something a browser would not, a test fails.

```
tests/visual/
├── cases/            one .html file per case (+ assets/ for images used by the cases)
├── references/       browser screenshots (committed) + manifest.json
├── harness.py        case loading, reference page template, image comparison
├── test_visual.py    the pytest test
└── _output/          expected/actual/diff images of failing cases (git-ignored)
```

## Running

```bash
pip install -e ".[dev]"
pytest tests/visual          # or just `pytest` to run everything
```

No browser is needed to run the tests: the references are committed. When a case fails,
look at `tests/visual/_output/<case>.{expected,actual,diff}.png` (differing pixels are
magenta in the diff).

## Writing a case

A case is a standalone HTML file: an optional metadata comment, a `<style>` block and the
markup. It can be opened directly in a browser.

```html
<!-- html2pic-test: {"max_diff_ratio": 0.02} -->
<style>
.card { width: 80px; height: 40px; border-radius: 8px; background-color: #3498db; }
</style>
<div class="card"></div>
```

Then generate its reference and **look at the PNG before committing it**:

```bash
pip install -e ".[dev,references]"
playwright install chromium       # once
python tools/generate_visual_references.py            # new or changed cases only
python tools/generate_visual_references.py my_case    # a specific case
python tools/generate_visual_references.py --all      # everything (e.g. after a browser upgrade)
```

If Playwright's bundled browser is not available, pass any Chromium binary with
`--executable /path/to/chrome` (or set `HTML2PIC_CHROMIUM`).

The manifest stores a hash of every case; editing a case without regenerating its
reference makes the test fail with a "stale reference" message.

### Naming

Prefix cases by area: `box_`, `flex_`, `position_`, `bg_`, `img_`, `shadow_`, `text_`,
`selectors_`. Cases that document a known divergence from browsers start with `gap_`.

Keep cases small and focused on one behaviour, so a failure points at one cause.

### Options

| Option | Default | Meaning |
|--------|---------|---------|
| `pixel_threshold` | `48` | A pixel differs when any premultiplied RGBA channel differs by more than this (0–255). |
| `max_diff_ratio` | `0.01` | Fraction of differing pixels allowed. |
| `shift_tolerance` | `0` | A pixel also matches if a reference pixel up to N px away matches. Use `1` for text (sub-pixel glyph positioning differs between engines); keep `0` for shapes so layout stays exact. |
| `size_tolerance` | `0` | Allowed difference, in px, between image sizes. |
| `xfail` | `null` | Reason string. Marks a **known divergence** from the browser. The test is a strict xfail: once html2pic is fixed it starts passing, the run fails, and the marker must be removed. |

Prefer fixing or isolating a difference over raising tolerances: if a case needs a large
tolerance, it is usually mixing two behaviours, and one of them deserves its own `gap_` case.

## How the reference page is built

`harness.PAGE_TEMPLATE` reproduces html2pic's rendering model so that only real
differences show up:

* html2pic has no user-agent stylesheet, so the page resets margins/padding and makes
  headings inherit font size and weight (every element starts at 16px, weight 400,
  line-height 1.2).
* The case is wrapped in an `inline-flex` column, which is what html2pic's root is
  (a PicTex `Column` cropped to its content).
* The default font is the Inter file bundled with PicTex, embedded in the page, so both
  engines use the same font.
* `font-optical-sizing` is disabled because PicTex does not set the `opsz` axis yet
  (see `gap_font_optical_sizing`).

Everything else (box sizing, margin collapsing, …) is left to the browser on purpose.
Changing the template requires bumping `TEMPLATE_VERSION` and regenerating all references.
