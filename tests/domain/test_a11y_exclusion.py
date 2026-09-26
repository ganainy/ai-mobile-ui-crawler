"""Tests for trimming the accessibility tree to the Status Bar / Bottom Bar Exclusion."""

from mobile_crawler.domain.crawler_agent.tools.ui.a11y_exclusion import exclude_bars

SCREEN_H = 2000


def node(top, bottom, text="", children=None):
    return {
        "text": text,
        "boundsInScreen": {"left": 0, "top": top, "right": 100, "bottom": bottom},
        "children": children or [],
    }


def texts(tree):
    out = []
    for child in tree["children"]:
        out.append(child["text"])
        out.extend(texts(child))
    return out


def test_drops_nodes_inside_top_and_bottom_strips():
    root = node(
        0,
        SCREEN_H,
        "root",
        [node(0, 80, "clock"), node(500, 600, "button"), node(1900, 2000, "nav")],
    )
    result = exclude_bars(root, SCREEN_H, top_px=80, bottom_px=100)
    assert texts(result) == ["button"]
    assert result["text"] == "root"


def test_keeps_nodes_that_overlap_a_strip():
    root = node(0, SCREEN_H, "root", [node(60, 300, "header"), node(1800, 1950, "footer")])
    result = exclude_bars(root, SCREEN_H, top_px=80, bottom_px=100)
    assert texts(result) == ["header", "footer"]


def test_survivors_of_a_dropped_container_move_up():
    root = node(0, SCREEN_H, "root", [node(0, 80, "bar", [node(500, 600, "odd child")])])
    result = exclude_bars(root, SCREEN_H, top_px=80, bottom_px=0)
    assert texts(result) == ["odd child"]


def test_no_exclusion_returns_tree_unchanged():
    root = node(0, SCREEN_H, "root", [node(0, 80, "clock")])
    assert exclude_bars(root, SCREEN_H, 0, 0) is root


def test_list_of_roots_and_missing_bounds():
    unbounded = {"text": "no bounds", "children": []}
    roots = [node(0, SCREEN_H, "a", [node(0, 50, "clock"), unbounded])]
    result = exclude_bars(roots, SCREEN_H, top_px=80, bottom_px=0)
    assert isinstance(result, list)
    assert texts(result[0]) == ["no bounds"]
