"""When is an accessibility tree trusted instead of running OmniParser?"""

from mobile_crawler.domain.crawler_agent.tools.ui.a11y_completeness import evaluate

SCREEN = {"screen_bounds": {"width": 1080, "height": 2400}}


def node(top, bottom, *, left=0, right=1080, cls="android.widget.TextView", text="", clickable=False, children=()):
    return {
        "className": cls,
        "text": text,
        "contentDescription": "",
        "isClickable": clickable,
        "boundsInScreen": {"left": left, "top": top, "right": right, "bottom": bottom},
        "children": list(children),
    }


def screen(*children):
    return node(0, 2400, cls="android.widget.FrameLayout", children=children)


def rows(count, *, clickable=True, text="row"):
    height = 2400 // count
    return [node(i * height, (i + 1) * height, text=text, clickable=clickable) for i in range(count)]


def test_full_screen_of_labelled_clickable_rows_is_trusted():
    assert evaluate(screen(*rows(6)), SCREEN) == []


def test_empty_tree_is_reported():
    assert evaluate([], SCREEN) == ["no_tree"]
    assert evaluate(None, SCREEN) == ["no_tree"]


def test_few_nodes():
    assert "few_nodes" in evaluate(screen(*rows(2)), SCREEN)


def test_webview_filling_the_screen_is_flagged():
    tree = screen(node(0, 2400, cls="android.webkit.WebView"), *rows(6, text="nav"))
    assert "surface_view" in evaluate(tree, SCREEN)


def test_small_webview_is_not_flagged():
    tree = screen(node(0, 300, cls="android.webkit.WebView"), *rows(6)[1:])
    assert "surface_view" not in evaluate(tree, SCREEN)


def test_text_only_screen_is_flagged():
    assert "text_only" in evaluate(screen(*rows(6, clickable=False)), SCREEN)


def test_a_couple_of_clickables_is_flagged_as_few():
    tree = screen(*rows(6)[:2], *rows(6, clickable=False)[2:])
    result = evaluate(tree, SCREEN)
    assert "few_clickables" in result
    assert "text_only" not in result


def test_labelled_nodes_covering_only_the_top_leave_the_screen_uncovered():
    top_only = [node(i * 100, (i + 1) * 100, text="row", clickable=True) for i in range(6)]
    assert "uncovered_area" in evaluate(screen(*top_only), SCREEN)


def test_twenty_text_nodes_and_one_unlabelled_custom_button_is_flagged():
    labels = [node(i * 60, i * 60 + 50, text="label", clickable=False) for i in range(20)]
    custom_button = node(2000, 2300, cls="android.view.View", clickable=True)
    result = evaluate(screen(*labels, custom_button), SCREEN)
    assert "few_clickables" in result
    assert "uncovered_area" in result


def test_unlabelled_full_screen_leaf_does_not_fake_coverage():
    blank = node(0, 2400, cls="android.view.View")
    assert "uncovered_area" in evaluate(screen(blank, *rows(6)[:1]), SCREEN)


def test_checks_can_be_disabled_and_tuned():
    tree = screen(*rows(6, clickable=False))
    assert "text_only" in evaluate(tree, SCREEN)
    assert "text_only" not in evaluate(tree, SCREEN, options={"disabled": ["text_only"]})
    two_clickables = screen(*rows(6)[:2], *rows(6, clickable=False)[2:])
    assert "few_clickables" not in evaluate(two_clickables, SCREEN, options={"min_clickables": 2})
