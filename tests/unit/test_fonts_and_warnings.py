import pytest

from html2pic.fonts import FontFace, FontRegistry, FontSrcParser
from html2pic.warnings import WarningCategory, WarningCollector
from html2pic.warnings.warning_collector import Html2PicWarning


class TestFontSrcParser:
    @pytest.mark.parametrize(
        "src, expected",
        [
            ("url(a.ttf)", "a.ttf"),
            ("url('a.ttf')", "a.ttf"),
            ('url("a b.ttf") format("truetype")', "a b.ttf"),
            ("local(Arial), url(b.woff2)", "b.woff2"),
            ("url(https://x.com/f.ttf)", "https://x.com/f.ttf"),
            ("local(Arial)", None),
            ("url(unterminated", None),
        ],
    )
    def test_parse(self, src, expected):
        assert FontSrcParser().parse(src) == expected


class TestFontRegistry:
    def test_resolves_registered_family_to_src(self):
        registry = FontRegistry()
        registry.add_font_face(FontFace(family="Brand", src="brand.ttf"))
        assert registry.resolve_font_family('"brand", Arial, sans-serif') == ["brand.ttf", "Arial", "sans-serif"]

    def test_unknown_family_is_passed_through(self):
        assert FontRegistry().resolve_font_family("Arial") == ["Arial"]

    def test_get_font_families_and_clear(self):
        registry = FontRegistry()
        registry.add_font_face(FontFace("A", "a.ttf"))
        registry.add_font_face(FontFace("A", "a-bold.ttf", weight="700"))
        registry.add_font_face(FontFace("B", "b.ttf"))
        assert sorted(registry.get_font_families()) == ["A", "B"]
        registry.clear()
        assert len(registry) == 0

    def test_font_face_matches(self):
        face = FontFace("Inter", "i.ttf", weight="700", style="italic")
        assert face.matches("inter", "700", "italic")
        assert not face.matches("inter", "400", "italic")


class TestWarningCollector:
    def test_collects_and_emits_python_warning(self):
        collector = WarningCollector()
        with pytest.warns(Html2PicWarning, match="boom"):
            collector.warn_message("boom")
        assert collector.get_warnings()[0]["category"] == "message"

    def test_filter_by_category(self):
        collector = WarningCollector()
        with pytest.warns(Html2PicWarning):
            collector.warn_unsupported_css_property("float", "left")
            collector.warn_unsupported_html_tag("script")
        assert len(collector.get_warnings(WarningCategory.CSS_PARSING)) == 1
        assert len(collector.get_warnings(WarningCategory.HTML_PARSING)) == 1

    def test_summary(self):
        collector = WarningCollector()
        with pytest.warns(Html2PicWarning):
            collector.warn_message("a")
            collector.warn_message("b")
            collector.warn_unexpected_error("c")
        summary = collector.get_summary()
        assert summary["total_warnings"] == 3
        assert summary["by_category"] == {"message": 2, "unexpected_error": 1}

    def test_disable(self):
        collector = WarningCollector()
        collector.disable()
        collector.warn_message("ignored")
        assert collector.get_warnings() == []

    def test_get_warnings_returns_copy(self):
        collector = WarningCollector()
        with pytest.warns(Html2PicWarning):
            collector.warn_message("a")
        collector.get_warnings().clear()
        assert len(collector.get_warnings()) == 1
