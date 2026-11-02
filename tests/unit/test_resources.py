import base64
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest

from html2pic.fetchers import FetchError, chain_fetchers, http_fetcher, local_fetcher
from html2pic.parsing import CssParser, HtmlParser
from html2pic.resources import ResourceLoader, Stylesheet, to_url
from html2pic.warnings import WarningCategory


def resource_warnings(collector):
    return [w["message"] for w in collector.get_warnings(WarningCategory.RESOURCE)]


class TestToUrl:
    def test_directory_gets_trailing_slash(self, tmp_path):
        assert to_url(str(tmp_path)).endswith("/")
        assert to_url(str(tmp_path)).startswith("file://")

    def test_file_path(self, tmp_path):
        f = tmp_path / "a.html"
        f.write_text("x")
        assert to_url(str(f)) == f.as_uri()

    def test_urls_are_kept(self):
        assert to_url("https://example.com/a/") == "https://example.com/a/"


class TestResolve:
    def test_relative_to_document_base(self, tmp_path):
        loader = ResourceLoader(base_url=str(tmp_path))
        assert loader.resolve("img/a.png") == (tmp_path / "img" / "a.png").as_uri()

    def test_relative_to_stylesheet(self):
        loader = ResourceLoader(base_url="https://site.test/page/")
        assert loader.resolve("../fonts/x.ttf", "https://cdn.test/css/main.css") == "https://cdn.test/fonts/x.ttf"

    def test_absolute_and_data_urls_are_untouched(self):
        loader = ResourceLoader(base_url="https://site.test/")
        assert loader.resolve("https://other.test/a.png") == "https://other.test/a.png"
        assert loader.resolve("data:text/plain,hi") == "data:text/plain,hi"

    def test_base_href_is_relative_to_original_base(self):
        loader = ResourceLoader(base_url="https://site.test/a/b/")
        loader.set_document_base("../assets/")
        assert loader.resolve("x.png") == "https://site.test/a/assets/x.png"

    def test_defaults_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert ResourceLoader().resolve("a.png") == (tmp_path / "a.png").as_uri()


class TestLocalize:
    def test_local_file_becomes_path(self, tmp_path):
        loader = ResourceLoader(base_url=str(tmp_path))
        assert loader.localize("a b.png") == str(tmp_path / "a b.png")

    def test_data_uri_is_written_to_temp_file(self):
        loader = ResourceLoader()
        payload = base64.b64encode(b"\x89PNG fake").decode()
        path = loader.localize(f"data:image/png;base64,{payload}")
        assert Path(path).read_bytes() == b"\x89PNG fake"

    def test_url_encoded_data_uri(self):
        loader = ResourceLoader()  # temp files live as long as the loader
        path = loader.localize("data:text/plain,hello%20world")
        assert Path(path).read_bytes() == b"hello world"

    def test_remote_without_fetcher_is_skipped_with_warning(self, warnings_collector):
        assert ResourceLoader().localize("https://x.test/a.png", purpose="image") is None
        assert "pass a `fetcher`" in resource_warnings(warnings_collector)[0]

    def test_remote_with_fetcher_is_downloaded_once(self):
        calls = []

        def fetcher(url):
            calls.append(url)
            return b"img-bytes"

        loader = ResourceLoader(fetcher=fetcher)
        first = loader.localize("https://x.test/a.png")
        second = loader.localize("https://x.test/a.png")
        assert first == second and first.endswith(".png")
        assert Path(first).read_bytes() == b"img-bytes"
        assert calls == ["https://x.test/a.png"]

    def test_fetcher_errors_become_warnings(self, warnings_collector):
        def fetcher(url):
            raise OSError("boom")

        assert ResourceLoader(fetcher=fetcher).localize("https://x.test/a.png") is None
        assert "boom" in resource_warnings(warnings_collector)[0]

    def test_unsupported_scheme(self, warnings_collector):
        assert ResourceLoader().localize("ftp://x.test/a.png") is None
        assert len(resource_warnings(warnings_collector)) == 1


    def test_temp_files_are_removed_with_the_loader(self):
        import gc

        loader = ResourceLoader()
        path = Path(loader.localize("data:text/plain,x"))
        assert path.exists()
        del loader
        gc.collect()
        assert not path.exists()


class TestFetchText:
    def test_requires_fetcher_even_for_local_files(self, tmp_path, warnings_collector):
        (tmp_path / "a.css").write_text("p{}")
        loader = ResourceLoader(base_url=str(tmp_path))
        assert loader.fetch_text(loader.resolve("a.css"), "stylesheet") is None
        assert len(resource_warnings(warnings_collector)) == 1

    def test_data_uri_stylesheet_needs_no_fetcher(self):
        assert ResourceLoader().fetch_text("data:text/css,p%7Bcolor:red%7D", "stylesheet") == "p{color:red}"


class TestLocalFetcher:
    def test_reads_files_inside_root(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "a.css").write_bytes(b"x")
        assert local_fetcher(tmp_path)((tmp_path / "sub" / "a.css").as_uri()) == b"x"

    def test_refuses_path_traversal(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        (tmp_path / "secret.txt").write_text("s")
        with pytest.raises(FetchError, match="outside"):
            local_fetcher(root)((root / ".." / "secret.txt").as_uri())

    def test_refuses_other_schemes(self, tmp_path):
        with pytest.raises(FetchError):
            local_fetcher(tmp_path)("https://x.test/a.css")


@pytest.fixture
def http_server(tmp_path):
    (tmp_path / "a.css").write_text("p { color: red }")
    (tmp_path / "big.bin").write_bytes(b"x" * 2048)
    handler = partial(SimpleHTTPRequestHandler, directory=str(tmp_path))
    handler.log_message = lambda *a: None
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


class TestHttpFetcher:
    def test_downloads(self, http_server):
        assert http_fetcher()(f"{http_server}/a.css") == b"p { color: red }"

    def test_size_limit(self, http_server):
        with pytest.raises(FetchError, match="larger"):
            http_fetcher(max_bytes=1024)(f"{http_server}/big.bin")

    def test_scheme_allowlist(self, http_server):
        with pytest.raises(FetchError):
            http_fetcher(allowed_schemes=("https",))(f"{http_server}/a.css")
        with pytest.raises(FetchError):
            http_fetcher()("file:///etc/passwd")

    def test_http_errors_raise(self, http_server):
        with pytest.raises(Exception):
            http_fetcher()(f"{http_server}/missing.css")


class TestChainFetchers:
    def test_first_success_wins(self):
        def fail(url):
            raise FetchError("nope")

        assert chain_fetchers(fail, lambda url: b"ok")("u") == b"ok"

    def test_all_fail(self):
        def fail(url):
            raise FetchError("nope")

        with pytest.raises(FetchError, match="nope; nope"):
            chain_fetchers(fail, fail)("u")


class TestHtmlParserMetadata:
    def test_collects_stylesheets_in_document_order(self):
        parser = HtmlParser()
        root = parser.parse(
            "<head><style>a{}</style><link rel='stylesheet' href='x.css'><link rel='icon' href='i.png'></head>"
            "<body><p>x</p><style>b{}</style></body>"
        )
        assert [(s.kind, s.value) for s in parser.stylesheets] == [("style", "a{}"), ("link", "x.css"), ("style", "b{}")]
        assert root.get_all_text() == "x"

    def test_base_href(self):
        parser = HtmlParser()
        parser.parse("<base href='assets/'><base href='ignored/'><p>x</p>")
        assert parser.base_href == "assets/"

    def test_print_only_stylesheets_are_ignored(self, warnings_collector):
        parser = HtmlParser()
        parser.parse("<style media='print'>a{}</style><link rel='stylesheet' href='p.css' media='print'><style media='all'>b{}</style>")
        assert [s.value for s in parser.stylesheets] == ["b{}"]
        assert len(warnings_collector.get_warnings()) == 2


class TestCssParserResources:
    def test_urls_are_resolved_against_the_sheet(self):
        parser = CssParser(loader=ResourceLoader(base_url="https://site.test/"))
        rules, registry = parser.parse_stylesheets([
            Stylesheet(".a { background-image: url(img/a.png) }", "https://cdn.test/css/main.css"),
            Stylesheet("@font-face { font-family: F; src: url('../f.ttf') } .b { background: url(b.png) red }", "https://site.test/x/"),
        ])
        assert rules[0].declarations["background-image"] == 'url("https://cdn.test/css/img/a.png")'
        assert rules[1].declarations["background-image"] == 'url("https://site.test/x/b.png")'
        assert registry.font_faces[0].src == "https://site.test/f.ttf"

    def test_later_sheets_come_later_in_cascade_order(self):
        rules, _ = CssParser().parse_stylesheets([Stylesheet("a { color: red }"), Stylesheet("b { color: blue }")])
        assert [r.selector for r in rules] == ["a", "b"]

    def test_font_faces_from_all_sheets_are_kept(self):
        _, registry = CssParser().parse_stylesheets([
            Stylesheet("@font-face { font-family: A; src: url(a.ttf) }"),
            Stylesheet("@font-face { font-family: B; src: url(b.ttf) }"),
        ])
        assert sorted(registry.get_font_families()) == ["A", "B"]

    def test_import(self):
        sheets = {"https://s.test/base.css": b"@import 'colors.css'; .b { color: blue }", "https://s.test/colors.css": b".a { color: red }"}
        parser = CssParser(loader=ResourceLoader(base_url="https://s.test/", fetcher=lambda url: sheets[url]))
        rules, _ = parser.parse('@import url("base.css"); .c { color: green }')
        assert [r.selector for r in rules] == [".a", ".b", ".c"]

    def test_import_cycle_is_broken(self, warnings_collector):
        sheets = {"https://s.test/a.css": b"@import 'b.css'; .a{}", "https://s.test/b.css": b"@import 'a.css'; .b{}"}
        parser = CssParser(loader=ResourceLoader(base_url="https://s.test/", fetcher=lambda url: sheets[url]))
        rules, _ = parser.parse("@import 'a.css';")
        assert [r.selector for r in rules] == [".b", ".a"]
        assert any("cycle" in m for m in resource_warnings(warnings_collector))

    def test_import_with_media_query_is_skipped(self, warnings_collector):
        parser = CssParser(loader=ResourceLoader(fetcher=lambda url: b".x{}"))
        rules, _ = parser.parse("@import 'p.css' print;")
        assert rules == []

    def test_import_without_fetcher_warns(self, warnings_collector):
        rules, _ = CssParser(loader=ResourceLoader()).parse("@import 'a.css'; p { color: red }")
        assert [r.selector for r in rules] == ["p"]
        assert len(resource_warnings(warnings_collector)) == 1

    def test_media_rules_are_skipped_not_misparsed(self, warnings_collector):
        rules, _ = CssParser().parse("@media (max-width: 100px) { p { color: red } } div { color: blue }")
        assert [r.selector for r in rules] == ["div"]

    def test_parse_inline(self):
        declarations = CssParser().parse_inline("color: red; padding: 1px 2px; background: url(a.png)")
        assert declarations["color"] == "red"
        assert declarations["padding-left"] == "2px"
        assert declarations["background-image"] == 'url("a.png")'
