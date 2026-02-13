"""Unit tests for OverlayRenderer."""

import pytest
from PIL import Image
from mobile_crawler.domain.overlay_renderer import OverlayRenderer

class TestOverlayRenderer:
    """Tests for OverlayRenderer class."""
    
    @pytest.fixture
    def renderer(self):
        return OverlayRenderer()
    
    @pytest.fixture
    def sample_image(self):
        return Image.new('RGB', (800, 600), color='white')
    
    def test_init(self, renderer):
        assert renderer is not None
        assert len(renderer.COLORS) == 5

    def test_validate_bbox(self, renderer):
        # Valid
        assert renderer._validate_bbox(10, 10, 100, 100, 800, 600) is True
        # Out of bounds
        assert renderer._validate_bbox(-1, 10, 100, 100, 800, 600) is False
        assert renderer._validate_bbox(10, 10, 801, 600, 800, 600) is False
        # Invalid orientation
        assert renderer._validate_bbox(100, 100, 50, 50, 800, 600) is False

    def test_render_overlays(self, renderer, sample_image):
        actions = [
            {
                "target_bounding_box": {
                    "top_left": [10, 10],
                    "bottom_right": [100, 100]
                }
            },
            {
                "target_bounding_box": {
                    "top_left": [200, 200],
                    "bottom_right": [300, 300]
                }
            }
        ]
        
        result = renderer.render_overlays(sample_image, actions)
        assert result is not None
        assert result.size == sample_image.size
        # Verify it's a new image object
        assert result is not sample_image

    def test_render_overlays_invalid_bbox(self, renderer, sample_image):
        actions = [
            {
                "target_bounding_box": {
                    "top_left": [-50, -50],
                    "bottom_right": [50, 50]
                }
            }
        ]
        # Should still render but with error color
        result = renderer.render_overlays(sample_image, actions)
        assert result is not None

    def test_render_overlays_empty_actions(self, renderer, sample_image):
        result = renderer.render_overlays(sample_image, [])
        assert result is not None
        assert result.size == sample_image.size

    def test_save_annotated(self, renderer, sample_image, tmp_path):
        actions = [
            {
                "target_bounding_box": {
                    "top_left": [10, 10],
                    "bottom_right": [100, 100]
                }
            }
        ]
        original_path = str(tmp_path / "step_001.png")
        sample_image.save(original_path)
        
        annotated_path = renderer.save_annotated(sample_image, actions, original_path)
        
        assert annotated_path != ""
        assert "step_001_annotated.png" in annotated_path
        from pathlib import Path
        assert Path(annotated_path).exists()
