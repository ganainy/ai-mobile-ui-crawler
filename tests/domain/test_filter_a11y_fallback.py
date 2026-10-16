from types import SimpleNamespace

from mobile_crawler.domain.crawler_agent.tools.filters.concise_filter import ConciseFilter
from mobile_crawler.domain.crawler_agent.tools.ui.provider import AndroidStateProvider

CTX = {"screen_bounds": {"width": 1080, "height": 2400}, "filtering_params": {}}


def node(left, top, right, bottom, **kw):
    return {"boundsInScreen": {"left": left, "top": top, "right": right, "bottom": bottom}, "children": [], **kw}


def call(tree):
    stub = SimpleNamespace(tree_filter=ConciseFilter())
    return AndroidStateProvider._filter_a11y_or_none(stub, tree, CTX)


def test_empty_tree_is_none():
    assert call([]) is None
    assert call(None) is None


def test_dict_root_is_filtered():
    out = call(node(0, 0, 1080, 2400, text="root"))
    assert out["text"] == "root"


def test_list_root_does_not_raise():
    out = call([node(0, 0, 1080, 1200, text="a"), node(0, 1200, 1080, 2400, text="b")])
    assert [c["text"] for c in out["children"]] == ["a", "b"]


def test_single_list_root_is_unwrapped():
    assert call([node(0, 0, 1080, 2400, text="only")])["text"] == "only"
