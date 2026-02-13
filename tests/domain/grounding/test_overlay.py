import os
import pytest
from PIL import Image
from mobile_crawler.domain.grounding.overlay import OverlayDrawer
from mobile_crawler.domain.grounding.dtos import OCRResult

@pytest.fixture
def sample_image(tmp_path):
    img_path = tmp_path / "test.png"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(img_path)
    return str(img_path)

def test_overlay_drawer_creates_file(sample_image, tmp_path):
    drawer = OverlayDrawer()
    results = [
        OCRResult(text="Test", box=(10, 10, 40, 40), confidence=0.9, center=(25, 25))
    ]
    output_path = str(tmp_path / "marked.png")
    
    saved_path = drawer.draw(sample_image, results, output_path)
    
    assert os.path.exists(saved_path)
    assert saved_path == output_path
    
    # Simple check that it's still an image
    with Image.open(saved_path) as img:
        assert img.size == (100, 100)
