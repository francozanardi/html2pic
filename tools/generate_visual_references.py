#!/usr/bin/env python
"""Render the visual test cases with a real browser and store them as reference images.

Usage:
    pip install -e ".[dev,references]"
    playwright install chromium            # once
    python tools/generate_visual_references.py            # only new or stale cases
    python tools/generate_visual_references.py --all      # regenerate everything
    python tools/generate_visual_references.py box_solid flex_row_gap

If Playwright's own browser build is not available you can point to any Chromium binary
with ``--executable`` (or the ``HTML2PIC_CHROMIUM`` environment variable).

The references are committed to the repository; tests/visual/test_visual.py compares
html2pic's output against them. Always review the generated PNGs before committing.
"""
import argparse
import io
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tests.visual.harness import (  # noqa: E402
    MANIFEST_PATH,
    REFERENCES_DIR,
    TEMPLATE_VERSION,
    inter_font_sha256,
    load_cases,
    load_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases", nargs="*", help="case names to (re)generate; default: new or stale cases")
    parser.add_argument("--all", action="store_true", help="regenerate every case")
    parser.add_argument("--executable", default=os.environ.get("HTML2PIC_CHROMIUM"), help="path to a Chromium binary")
    parser.add_argument("--prune", action="store_true", help="delete references whose case no longer exists")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
        from PIL import Image
    except ImportError:
        print('Missing dependencies. Install them with: pip install -e ".[dev,references]"', file=sys.stderr)
        return 1

    cases = {case.name: case for case in load_cases()}
    manifest = load_manifest()
    entries = manifest.setdefault("cases", {})

    unknown = [name for name in args.cases if name not in cases]
    if unknown:
        print(f"Unknown case(s): {', '.join(unknown)}", file=sys.stderr)
        return 1

    if args.cases:
        selected = [cases[name] for name in args.cases]
    elif args.all:
        selected = list(cases.values())
    else:
        selected = [
            case for case in cases.values()
            if not case.reference_path.exists() or entries.get(case.name, {}).get("source_sha256") != case.source_hash
        ]

    if args.prune:
        for name in sorted(set(entries) - set(cases)):
            (REFERENCES_DIR / f"{name}.png").unlink(missing_ok=True)
            del entries[name]
            print(f"pruned  {name}")

    if not selected:
        print("All references are up to date.")
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        launch_kwargs = {"executable_path": args.executable} if args.executable else {}
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(device_scale_factor=1, viewport={"width": 1200, "height": 900})

        # The page must be loaded from a file:// URL: Chromium refuses to load file://
        # subresources (images used by the cases) into a page created with set_content().
        with tempfile.TemporaryDirectory() as tmp:
            page_path = Path(tmp) / "case.html"
            for case in selected:
                page_path.write_text(case.browser_page(), encoding="utf-8")
                page.goto(page_path.as_uri(), wait_until="load")
                page.evaluate("document.fonts.ready")
                broken = page.evaluate("[...document.images].filter(i => !i.complete || !i.naturalWidth).map(i => i.src)")
                if broken:
                    raise RuntimeError(f"{case.name}: images failed to load: {broken}")
                png = page.locator("#__html2pic_capture").screenshot(omit_background=True, animations="disabled")
                Image.open(io.BytesIO(png)).convert("RGBA").save(case.reference_path, optimize=True)
                entries[case.name] = {"source_sha256": case.source_hash}
                print(f"wrote   {case.reference_path.relative_to(REPO_ROOT)}")

        manifest.update({
            "browser": f"chromium {browser.version}",
            "template_version": TEMPLATE_VERSION,
            "inter_font_sha256": inter_font_sha256(),
        })
        if selected:
            manifest["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        browser.close()

    manifest["cases"] = dict(sorted(entries.items()))
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
