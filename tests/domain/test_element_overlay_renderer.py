"""ElementOverlayRenderer must translate absolute-device bounds onto a
screenshot that's already had Status Bar Exclusion cropped off (ADR-0002).

element['bounds'] is always in absolute device coordinates (needed for
tapping, see UIState.get_element_coords), but the screenshot passed to
render() may already be cropped — top_offset_px bridges the two coordinate
spaces so the drawn box lands on the element it labels.
"""

from PIL import Image

from mobile_crawler.domain.element_overlay_renderer import ElementOverlayRenderer


def _pixel(img: Image.Image, x: int, y: int) -> tuple:
    return img.convert("RGB").getpixel((x, y))


def test_bounds_align_without_offset_when_image_uncropped():
    renderer = ElementOverlayRenderer()
    image = Image.new("RGB", (100, 100), color="white")
    elements = [{"index": 1, "bounds": "10,10,30,30"}]

    result = renderer.render(image, elements)

    # Top-left corner of the drawn rectangle should be at (10, 10).
    assert _pixel(result, 10, 10) != (255, 255, 255)


def test_bounds_shifted_up_by_top_offset_for_cropped_image():
    renderer = ElementOverlayRenderer()
    # Image already had the top 20px cropped off (ADR-0002).
    cropped_image = Image.new("RGB", (100, 80), color="white")
    # Element bounds are absolute device coordinates, e.g. y=20..40 in the
    # original (uncropped) 100x100 frame -> y=0..20 in the cropped image.
    elements = [{"index": 1, "bounds": "10,20,30,40"}]

    result = renderer.render(cropped_image, elements, top_offset_px=20)

    assert _pixel(result, 10, 0) != (255, 255, 255)


def test_element_still_in_excluded_band_is_skipped():
    renderer = ElementOverlayRenderer()
    cropped_image = Image.new("RGB", (100, 80), color="white")
    # This element's absolute bounds are entirely within the cropped-off
    # top 20px band -> after offsetting, y1/y2 go negative and it must not
    # be drawn (nothing there to draw it onto).
    elements = [{"index": 1, "bounds": "10,0,30,15"}]

    result = renderer.render(cropped_image, elements, top_offset_px=20)

    assert _pixel(result, 15, 0) == (255, 255, 255)
