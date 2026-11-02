"""Compare html2pic renders against reference images produced by a real browser.

References live in tests/visual/references and are generated with
``python tools/generate_visual_references.py``. On failure, the expected, actual and
diff images are written to tests/visual/_output/ for inspection.
"""
import numpy as np
import pytest

from html2pic import Html2Pic

from .harness import OUTPUT_DIR, CASES_DIR, compare_images, diff_image, load_cases, load_manifest

Image = pytest.importorskip("PIL.Image", reason="Pillow is required for visual tests (pip install -e '.[dev]')")

CASES = load_cases()
MANIFEST = load_manifest()


def _params():
    for case in CASES:
        marks = []
        if case.options["xfail"]:
            marks.append(pytest.mark.xfail(reason=case.options["xfail"], strict=True))
        yield pytest.param(case, id=case.name, marks=marks)


@pytest.mark.visual
@pytest.mark.parametrize("case", list(_params()))
def test_matches_browser_reference(case, monkeypatch):
    if not case.reference_path.exists():
        pytest.fail(f"missing reference for '{case.name}': run tools/generate_visual_references.py {case.name}")
    if MANIFEST["cases"].get(case.name, {}).get("source_sha256") != case.source_hash:
        pytest.fail(f"reference for '{case.name}' is stale: run tools/generate_visual_references.py {case.name}")

    expected = np.asarray(Image.open(case.reference_path).convert("RGBA"))

    # Relative url()s in cases are resolved against the cases directory, like the browser's <base>.
    monkeypatch.chdir(CASES_DIR)
    actual = Html2Pic(case.html, case.css).render().to_numpy("RGBA")

    passed, result = compare_images(expected, actual, case.options)
    if not passed:
        OUTPUT_DIR.mkdir(exist_ok=True)
        Image.fromarray(expected).save(OUTPUT_DIR / f"{case.name}.expected.png")
        Image.fromarray(actual).save(OUTPUT_DIR / f"{case.name}.actual.png")
        if result.diff_mask is not None:
            Image.fromarray(diff_image(expected, actual, result.diff_mask)).save(OUTPUT_DIR / f"{case.name}.diff.png")
        pytest.fail(
            f"{case.name}: {result.summary()} "
            f"(allowed {case.options['max_diff_ratio']:.2%}); see tests/visual/_output/{case.name}.*.png",
            pytrace=False,
        )
