"""End-to-end tests for stylesheets, style attributes and external resources."""
import base64
import contextlib
import io
import shutil
from importlib import resources
import warnings
from pathlib import Path

import pytest

from html2pic import Html2Pic
from html2pic.fetchers import local_fetcher
from html2pic.warnings import WarningCategory

PIL = pytest.importorskip("PIL.Image")

RED = (255, 0, 0, 255)
GREEN = (0, 128, 0, 255)
BLUE = (0, 0, 255, 255)


def px(img, x, y):
    return tuple(int(c) for c in img[y, x])


def png_bytes(color, size=(4, 4)):
    buf = io.BytesIO()
    PIL.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


def render(html, css="", **kwargs):
    return Html2Pic(html, css, **kwargs).render().to_numpy("RGBA")


BOX = "width: 10px; height: 10px;"


class TestStyleTags:
    def test_style_tag_is_applied(self):
        img = render(f"<style>.b {{ {BOX} background-color: red }}</style><div class='b'></div>")
        assert px(img, 5, 5) == RED

    def test_full_document_with_head(self):
        html = f"""<!doctype html><html><head><title>x</title>
        <style>.b {{ {BOX} background-color: blue }}</style></head>
        <body><div class="b"></div></body></html>"""
        img = render(html)
        assert img.shape[:2] == (10, 10)
        assert px(img, 5, 5) == BLUE

    def test_css_argument_wins_ties_over_style_tags(self):
        img = render(f"<style>.b {{ {BOX} background-color: red }}</style><div class='b'></div>", ".b { background-color: blue }")
        assert px(img, 5, 5) == BLUE

    def test_specificity_still_beats_order(self):
        img = render(f"<style>#x {{ {BOX} background-color: red }}</style><div id='x' class='b'></div>", ".b { background-color: blue }")
        assert px(img, 5, 5) == RED


class TestStyleAttribute:
    def test_applied(self):
        assert px(render(f"<div style='{BOX} background-color: red'></div>"), 5, 5) == RED

    def test_beats_any_selector(self):
        img = render(f"<div id='x' style='background-color: blue'></div>", f"#x {{ {BOX} background-color: red }}")
        assert px(img, 5, 5) == BLUE

    def test_shorthands_and_inheritance(self):
        img = render("<div style='padding: 5px; background: red; color: blue'><p style='width: 4px; height: 4px; background-color: blue'></p></div>")
        assert img.shape[:2] == (14, 14)
        assert px(img, 1, 1) == RED


class TestImages:
    def test_relative_to_base_url(self, tmp_path):
        (tmp_path / "img").mkdir()
        (tmp_path / "img" / "r.png").write_bytes(png_bytes((255, 0, 0, 255)))
        img = render("<img src='img/r.png' class='i'>", ".i { width: 8px; height: 8px }", base_url=str(tmp_path))
        assert px(img, 4, 4) == RED

    def test_base_href(self, tmp_path):
        (tmp_path / "assets").mkdir()
        (tmp_path / "assets" / "r.png").write_bytes(png_bytes((255, 0, 0, 255)))
        html = "<head><base href='assets/'></head><img src='r.png' class='i'>"
        img = render(html, ".i { width: 8px; height: 8px }", base_url=str(tmp_path))
        assert px(img, 4, 4) == RED

    def test_data_uri(self):
        uri = "data:image/png;base64," + base64.b64encode(png_bytes((0, 0, 255, 255))).decode()
        img = render(f"<img src='{uri}' class='i'>", ".i { width: 8px; height: 8px }")
        assert px(img, 4, 4) == BLUE

    def test_remote_image_through_fetcher(self):
        calls = []

        def fetcher(url):
            calls.append(url)
            return png_bytes((255, 0, 0, 255))

        img = render("<img src='https://cdn.test/r.png' class='i'>", ".i { width: 8px; height: 8px }", fetcher=fetcher)
        assert px(img, 4, 4) == RED
        assert calls == ["https://cdn.test/r.png"]

    def test_remote_image_without_fetcher_is_skipped(self):
        h = Html2Pic("<img src='https://cdn.test/r.png' class='i'><div class='b'></div>", f".i {{ width: 8px; height: 8px }} .b {{ {BOX} background-color: red }}")
        img = h.render().to_numpy("RGBA")
        assert img.shape[:2] == (10, 10)
        assert any("cdn.test" in w["message"] for w in h.get_warnings())

    def test_background_image_relative_to_linked_stylesheet(self, tmp_path):
        (tmp_path / "css").mkdir()
        (tmp_path / "img").mkdir()
        (tmp_path / "img" / "b.png").write_bytes(png_bytes((0, 0, 255, 255)))
        (tmp_path / "css" / "site.css").write_text(f".b {{ {BOX} background-image: url(../img/b.png) }}")
        html = "<link rel='stylesheet' href='css/site.css'><div class='b'></div>"
        img = render(html, base_url=str(tmp_path), fetcher=local_fetcher(tmp_path))
        assert px(img, 5, 5) == BLUE


class TestLinkedStylesheets:
    def test_link_with_fetcher(self, tmp_path):
        (tmp_path / "a.css").write_text(f".b {{ {BOX} background-color: green }}")
        img = render("<link rel='stylesheet' href='a.css'><div class='b'></div>", base_url=str(tmp_path), fetcher=local_fetcher(tmp_path))
        assert px(img, 5, 5) == GREEN

    def test_link_without_fetcher_warns(self, tmp_path):
        (tmp_path / "a.css").write_text(".b { background-color: green }")
        h = Html2Pic(f"<link rel='stylesheet' href='a.css'><div class='b' style='{BOX} background-color: red'></div>", base_url=str(tmp_path))
        assert px(h.render().to_numpy("RGBA"), 5, 5) == RED
        assert len(h._warnings.get_warnings(WarningCategory.RESOURCE)) == 1

    def test_import_inside_style_tag(self, tmp_path):
        (tmp_path / "theme.css").write_text(f".b {{ {BOX} background-color: blue }}")
        html = "<style>@import 'theme.css';</style><div class='b'></div>"
        img = render(html, base_url=str(tmp_path), fetcher=local_fetcher(tmp_path))
        assert px(img, 5, 5) == BLUE

    def test_link_order_relative_to_style_tags(self, tmp_path):
        (tmp_path / "a.css").write_text(".b { background-color: blue }")
        html = f"<style>.b {{ {BOX} background-color: red }}</style><link rel='stylesheet' href='a.css'><div class='b'></div>"
        img = render(html, base_url=str(tmp_path), fetcher=local_fetcher(tmp_path))
        assert px(img, 5, 5) == BLUE


class TestFonts:
    @pytest.fixture
    def font_dir(self, tmp_path):
        shutil.copy(Path(str(resources.files("pictex") / "fonts" / "InterVariable.ttf")), tmp_path / "Brand.ttf")
        return tmp_path

    def test_font_face_relative_to_base_url(self, font_dir):
        css = "@font-face { font-family: Brand; src: url(Brand.ttf) } p { font-family: Brand; font-size: 20px }"
        with no_font_warning():
            Html2Pic("<p>Hi</p>", css, base_url=str(font_dir)).render()

    def test_missing_font_is_reported(self, tmp_path):
        css = "@font-face { font-family: Brand; src: url(missing.ttf) } p { font-family: Brand }"
        with pytest.raises(AssertionError):
            with no_font_warning():
                Html2Pic("<p>Hi</p>", css, base_url=str(tmp_path)).render()

    def test_remote_font_through_fetcher(self, font_dir):
        calls = []

        def fetcher(url):
            calls.append(url)
            return (font_dir / "Brand.ttf").read_bytes()

        css = "@font-face { font-family: Brand; src: url(https://fonts.test/brand.ttf) } p { font-family: Brand }"
        with no_font_warning():
            Html2Pic("<p>Hi</p>", css, fetcher=fetcher).render()
        assert calls == ["https://fonts.test/brand.ttf"]


@contextlib.contextmanager
def no_font_warning():
    """Fail if PicTex reports that a font could not be loaded."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        yield
    problems = [str(w.message) for w in caught if "not found" in str(w.message).lower()]
    assert not problems, problems
