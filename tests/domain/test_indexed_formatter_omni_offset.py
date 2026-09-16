"""IndexedFormatter must offset OmniParser bbox ratios by status_bar_exclusion_px.

OmniParser runs on a screenshot already cropped by status_bar_exclusion_px
(ADR-0002), so its [x1, y1, x2, y2] ratios are relative to the *cropped*
image height, not the full device height. Converting them back to absolute
device coordinates for tapping requires scaling against the cropped height
and adding the crop back as an offset.
"""

from mobile_crawler.domain.crawler_agent.tools.formatters.indexed_formatter import IndexedFormatter


def test_omni_bbox_offset_by_status_bar_exclusion():
    formatter = IndexedFormatter()
    formatter.screen_width = 1000
    formatter.screen_height = 2000
    formatter.status_bar_exclusion_px = 100

    # An element pinned to the very top of the *cropped* screenshot (ratio 0)
    # must land at the crop offset in absolute device coordinates, not at 0.
    omni_tree = [
        {"bbox": [0.0, 0.0, 1.0, 1.0], "content": "full cropped frame", "type": "text"}
    ]

    indexed = formatter._convert_omni_to_indexed(omni_tree)

    assert indexed[0]["bounds"] == "0,100,1000,2000"


def test_omni_bbox_offset_zero_matches_unadjusted_math():
    formatter = IndexedFormatter()
    formatter.screen_width = 1000
    formatter.screen_height = 2000
    formatter.status_bar_exclusion_px = 0

    omni_tree = [{"bbox": [0.1, 0.2, 0.5, 0.6], "content": "elem", "type": "text"}]

    indexed = formatter._convert_omni_to_indexed(omni_tree)

    assert indexed[0]["bounds"] == "100,400,500,1200"


def test_omni_bbox_bottom_exclusion_shrinks_denominator_without_offset():
    formatter = IndexedFormatter()
    formatter.screen_width = 1000
    formatter.screen_height = 2000
    formatter.status_bar_exclusion_px = 0
    formatter.bottom_bar_exclusion_px = 100

    # ratio 0 still lands at absolute 0 - bottom crop doesn't move the origin,
    # it only shrinks the cropped image the ratios are relative to.
    omni_tree = [{"bbox": [0.0, 0.0, 1.0, 1.0], "content": "full cropped frame", "type": "text"}]

    indexed = formatter._convert_omni_to_indexed(omni_tree)

    assert indexed[0]["bounds"] == "0,0,1000,1900"


def test_omni_bbox_top_and_bottom_exclusion_combine():
    formatter = IndexedFormatter()
    formatter.screen_width = 1000
    formatter.screen_height = 2000
    formatter.status_bar_exclusion_px = 100
    formatter.bottom_bar_exclusion_px = 100

    omni_tree = [{"bbox": [0.0, 0.0, 1.0, 1.0], "content": "full cropped frame", "type": "text"}]

    indexed = formatter._convert_omni_to_indexed(omni_tree)

    assert indexed[0]["bounds"] == "0,100,1000,1900"
