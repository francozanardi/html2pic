"""End-to-end tests: render real images and assert on their size and pixels."""
import runpy
import shutil
from pathlib import Path

import pytest

from html2pic import Html2Pic, RenderError

RED = (255, 0, 0, 255)
BLUE = (0, 0, 255, 255)
TRANSPARENT = (0, 0, 0, 0)


def px(img, x, y):
    return tuple(int(c) for c in img[y, x])


def box(width, height, color="red", extra=""):
    return f"width: {width}px; height: {height}px; background-color: {color}; {extra}"


class TestBasicRendering:
    def test_fixed_size_box(self, render_rgba):
        img = render_rgba('<div class="b"></div>', f".b {{ {box(40, 20)} }}")
        assert img.shape == (20, 40, 4)
        assert px(img, 0, 0) == RED
        assert px(img, 39, 19) == RED

    def test_background_alpha(self, render_rgba):
        img = render_rgba('<div class="b"></div>', ".b { width: 4px; height: 4px; background-color: rgba(0, 0, 255, 0.5) }")
        r, g, b, a = px(img, 2, 2)
        assert a == pytest.approx(127, abs=2)
        assert b > 0 and r == 0 and g == 0

    def test_padding_grows_box(self, render_rgba):
        css = f".o {{ padding: 5px; background-color: blue }} .i {{ {box(10, 10)} }}"
        img = render_rgba('<div class="o"><div class="i"></div></div>', css)
        assert img.shape[:2] == (20, 20)
        assert px(img, 1, 1) == BLUE
        assert px(img, 10, 10) == RED

    def test_border(self, render_rgba):
        css = f".b {{ {box(20, 20, 'red', 'border: 3px solid blue;')} }}"
        img = render_rgba('<div class="b"></div>', css)
        assert px(img, 1, 10) == BLUE
        assert px(img, 10, 10) == RED

    def test_display_none_hides_element(self, render_rgba):
        css = f".a {{ {box(10, 10)} }} .h {{ display: none; {box(50, 50, 'blue')} }}"
        img = render_rgba('<div class="a"></div><div class="h"></div>', css)
        assert img.shape[:2] == (10, 10)

    def test_text_renders_some_ink(self, render_rgba):
        img = render_rgba("<p>Hello</p>", "p { color: black; font-size: 30px }")
        assert img.shape[0] >= 30
        assert img[..., 3].max() == 255

    def test_empty_document_raises_render_error(self):
        with pytest.raises(RenderError):
            Html2Pic("", "").render()

    def test_render_as_svg(self):
        svg = Html2Pic('<div class="b"></div>', f".b {{ {box(10, 10)} }}").render_as_svg()
        assert "<svg" in svg.svg

    def test_render_error_is_wrapped(self):
        with pytest.raises(RenderError):
            Html2Pic('<img src="/does/not/exist.png">').render()


class TestFlexbox:
    def test_row_lays_children_side_by_side(self, render_rgba):
        css = f".r {{ display: flex; flex-direction: row }} .a {{ {box(10, 10)} }} .b {{ {box(10, 10, 'blue')} }}"
        img = render_rgba('<div class="r"><div class="a"></div><div class="b"></div></div>', css)
        assert img.shape[:2] == (10, 20)
        assert px(img, 5, 5) == RED
        assert px(img, 15, 5) == BLUE

    def test_column_stacks_children(self, render_rgba):
        css = f".c {{ display: flex; flex-direction: column }} .a {{ {box(10, 10)} }} .b {{ {box(10, 10, 'blue')} }}"
        img = render_rgba('<div class="c"><div class="a"></div><div class="b"></div></div>', css)
        assert img.shape[:2] == (20, 10)
        assert px(img, 5, 15) == BLUE

    def test_gap(self, render_rgba):
        css = f".r {{ display: flex; gap: 6px }} .a {{ {box(10, 10)} }}"
        img = render_rgba('<div class="r"><div class="a"></div><div class="a"></div></div>', css)
        assert img.shape[:2] == (10, 26)
        assert px(img, 13, 5) == TRANSPARENT

    def test_justify_content_center(self, render_rgba):
        css = f".r {{ display: flex; width: 30px; justify-content: center }} .a {{ {box(10, 10)} }}"
        img = render_rgba('<div class="r"><div class="a"></div></div>', css)
        assert px(img, 5, 5) == TRANSPARENT
        assert px(img, 15, 5) == RED

    def test_flex_grow_fills_space(self, render_rgba):
        css = f".r {{ display: flex; width: 40px }} .a {{ {box(10, 10)} }} .g {{ flex-grow: 1; height: 10px; background-color: blue }}"
        img = render_rgba('<div class="r"><div class="a"></div><div class="g"></div></div>', css)
        assert px(img, 39, 5) == BLUE

    def test_absolute_position(self, render_rgba):
        css = (
            f".p {{ {box(30, 30, 'blue')} }}"
            f".c {{ position: absolute; top: 10px; left: 10px; {box(5, 5)} }}"
        )
        img = render_rgba('<div class="p"><div class="c"></div></div>', css)
        assert px(img, 12, 12) == RED
        assert px(img, 5, 5) == BLUE


class TestBackgrounds:
    def test_linear_gradient_left_to_right(self, render_rgba):
        css = ".g { width: 100px; height: 10px; background-image: linear-gradient(to right, red, blue) }"
        img = render_rgba('<div class="g"></div>', css)
        left, right = px(img, 1, 5), px(img, 98, 5)
        assert left[0] > 240 and left[2] < 15
        assert right[2] > 240 and right[0] < 15

    def test_border_radius_clips_corners(self, render_rgba):
        img = render_rgba('<div class="b"></div>', f".b {{ {box(40, 40, 'red', 'border-radius: 20px;')} }}")
        assert px(img, 0, 0)[3] == 0
        assert px(img, 20, 20) == RED

    def test_box_shadow_extends_beyond_box(self):
        css = f".b {{ {box(10, 10, 'red', 'box-shadow: 5px 5px 0 blue;')} }}"
        img = Html2Pic('<div class="b"></div>', css).render(crop_mode="none").to_numpy("RGBA")
        assert (img[..., 2] == 255).any()


EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


@pytest.mark.parametrize("script", sorted(EXAMPLES_DIR.glob("0*.py")), ids=lambda p: p.name)
def test_examples_run(script, tmp_path, monkeypatch):
    """Every example script must run without errors (outputs go to a temp dir)."""
    for asset in EXAMPLES_DIR.iterdir():
        if asset.suffix != ".py":
            shutil.copy(asset, tmp_path)
    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(script), run_name="__main__")


def test_render_does_not_write_debug_output_for_transforms(capsys):
    css = ".b { width: 10px; height: 10px; background-color: red; transform: translate(2px, 2px) }"
    Html2Pic('<div class="b"></div>', css).render()
    assert "translate_x" not in capsys.readouterr().out


@pytest.mark.parametrize("selector", ["div", "*"])
def test_type_and_universal_selectors_do_not_pad_synthetic_root(render_rgba, selector):
    css = f"{selector} {{ padding: 10px }} p {{ width: 10px; height: 10px; background-color: red; padding: 0 }}"
    img = render_rgba("<div><p></p></div>", css)
    assert img.shape[:2] == (30, 30)


class TestUnits:
    def test_percentage_width_resolves_against_parent(self, render_rgba):
        css = ".p { width: 100px; height: 10px } .c { width: 50%; height: 10px; background-color: red }"
        img = render_rgba('<div class="p"><div class="c"></div></div>', css)
        assert px(img, 45, 5) == RED
        assert px(img, 55, 5) == TRANSPARENT

    def test_percentage_border_radius_makes_a_circle(self, render_rgba):
        img = render_rgba('<div class="b"></div>', f".b {{ {box(40, 40, 'red', 'border-radius: 50%;')} }}")
        assert px(img, 0, 0)[3] == 0
        assert px(img, 3, 3)[3] == 0  # ~24px from the centre: outside the r=20 circle
        assert px(img, 20, 20) == RED

    def test_rem_sizes(self, render_rgba):
        img = render_rgba('<div class="b"></div>', ".b { width: 2rem; height: 1rem; background-color: red }")
        assert img.shape[:2] == (16, 32)

    def test_em_font_size_is_relative_to_parent(self, render_rgba):
        small = render_rgba('<div class="p"><p>Hg</p></div>', ".p { font-size: 10px } p { font-size: 2em }")
        big = render_rgba('<div class="p"><p>Hg</p></div>', ".p { font-size: 40px } p { font-size: 2em }")
        assert big.shape[0] > small.shape[0] * 1.5


class TestBackgroundShorthand:
    def test_solid_color(self, render_rgba):
        img = render_rgba('<div class="b"></div>', ".b { width: 10px; height: 10px; background: red }")
        assert px(img, 5, 5) == RED

    def test_gradient_as_used_in_readme_quick_start(self, render_rgba):
        css = ".g { width: 100px; height: 10px; background: linear-gradient(to right, red, blue) }"
        img = render_rgba('<div class="g"></div>', css)
        assert px(img, 1, 5)[0] > 240
        assert px(img, 98, 5)[2] > 240

    def test_unsupported_image_warns(self, warnings_collector):
        css = ".g { width: 10px; height: 10px; background: radial-gradient(red, blue) }"
        Html2Pic('<div class="g"></div>', css).render()
        assert any("radial-gradient" in w["message"] for w in warnings_collector.get_warnings())


class TestColors:
    @pytest.mark.parametrize("color", ["rgb(255 0 0)", "hsl(0, 100%, 50%)", "rgb(100% 0% 0%)"])
    def test_modern_color_syntaxes_render(self, render_rgba, color):
        img = render_rgba('<div class="b"></div>', f".b {{ width: 4px; height: 4px; background-color: {color} }}")
        assert px(img, 2, 2) == RED

    def test_rgba_gradient_stops(self, render_rgba, warnings_collector):
        css = ".g { width: 100px; height: 4px; background-image: linear-gradient(to right, rgba(255, 0, 0, 1), hsl(240, 100%, 50%)) }"
        img = render_rgba('<div class="g"></div>', css)
        assert warnings_collector.get_warnings() == []
        assert px(img, 1, 2)[0] > 240
        assert px(img, 98, 2)[2] > 240


def test_descendant_selectors_render(render_rgba):
    css = (
        ".wrap { display: flex }"
        ".wrap .box { width: 10px; height: 10px; background-color: red }"
        ".box { width: 10px; height: 10px; background-color: blue }"
    )
    img = render_rgba('<div class="wrap"><div class="box"></div></div><div class="box"></div>', css)
    assert px(img, 5, 5) == RED
    assert px(img, 5, 15) == BLUE
