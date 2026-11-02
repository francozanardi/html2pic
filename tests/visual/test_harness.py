"""Tests for the visual test harness itself (comparison and case loading)."""
import numpy as np
import pytest

from .harness import DEFAULT_OPTIONS, compare_images, load_case


def solid(h, w, rgba):
    return np.tile(np.array(rgba, dtype=np.uint8), (h, w, 1))


def opts(**kw):
    return dict(DEFAULT_OPTIONS, **kw)


class TestCompareImages:
    def test_identical(self):
        img = solid(5, 5, (10, 20, 30, 255))
        passed, result = compare_images(img, img.copy(), opts())
        assert passed and result.diff_ratio == 0

    def test_size_mismatch_fails(self):
        passed, result = compare_images(solid(5, 5, (0, 0, 0, 255)), solid(5, 6, (0, 0, 0, 255)), opts())
        assert not passed and result.diff_mask is None
        assert "size" in result.summary()

    def test_size_tolerance(self):
        passed, _ = compare_images(solid(10, 10, (0, 0, 0, 0)), solid(10, 11, (0, 0, 0, 0)), opts(size_tolerance=1))
        assert passed

    def test_small_channel_differences_are_ignored(self):
        passed, _ = compare_images(solid(4, 4, (100, 100, 100, 255)), solid(4, 4, (130, 100, 100, 255)), opts())
        assert passed

    def test_color_differences_are_detected(self):
        passed, result = compare_images(solid(4, 4, (255, 0, 0, 255)), solid(4, 4, (0, 0, 255, 255)), opts())
        assert not passed and result.diff_ratio == 1.0

    def test_fully_transparent_pixels_compare_equal_regardless_of_rgb(self):
        passed, _ = compare_images(solid(4, 4, (255, 0, 0, 0)), solid(4, 4, (0, 255, 0, 0)), opts())
        assert passed

    def test_ratio_threshold(self):
        expected = solid(10, 10, (0, 0, 0, 255))
        actual = expected.copy()
        actual[0, :5] = (255, 255, 255, 255)  # 5% of pixels
        assert not compare_images(expected, actual, opts(max_diff_ratio=0.04))[0]
        assert compare_images(expected, actual, opts(max_diff_ratio=0.05))[0]

    def test_shift_tolerance_absorbs_one_pixel_offsets_only(self):
        expected = solid(10, 10, (255, 255, 255, 255))
        expected[:, 4] = (0, 0, 0, 255)
        one_px = np.roll(expected, 1, axis=1)
        two_px = np.roll(expected, 2, axis=1)
        assert not compare_images(expected, one_px, opts(max_diff_ratio=0))[0]
        assert compare_images(expected, one_px, opts(max_diff_ratio=0, shift_tolerance=1))[0]
        assert not compare_images(expected, two_px, opts(max_diff_ratio=0, shift_tolerance=1))[0]


class TestLoadCase:
    def test_parses_metadata_style_and_markup(self, tmp_path):
        path = tmp_path / "c.html"
        path.write_text('<!-- html2pic-test: {"max_diff_ratio": 0.5} -->\n<style>p { color: red }</style>\n<p>x</p>\n')
        case = load_case(path)
        assert case.name == "c"
        assert case.options["max_diff_ratio"] == 0.5
        assert case.options["pixel_threshold"] == DEFAULT_OPTIONS["pixel_threshold"]
        assert case.css.strip() == "p { color: red }"
        assert case.html == "<p>x</p>"

    def test_unknown_option_is_rejected(self, tmp_path):
        path = tmp_path / "c.html"
        path.write_text('<!-- html2pic-test: {"max_diff": 1} --><p>x</p>')
        with pytest.raises(ValueError, match="max_diff"):
            load_case(path)

    def test_hash_changes_with_content(self, tmp_path):
        path = tmp_path / "c.html"
        path.write_text("<p>a</p>")
        before = load_case(path).source_hash
        path.write_text("<p>b</p>")
        assert load_case(path).source_hash != before
