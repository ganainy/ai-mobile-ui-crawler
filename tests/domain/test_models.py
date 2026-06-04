"""Tests for domain data models."""

import pytest

from mobile_crawler.domain.models import (
    ActionResult,
    AIAction,
    AIResponse,
    BoundingBox,
    UIElement,
)


class TestUIElement:
    """Tests for UIElement dataclass."""

    def test_construction_with_required_fields(self):
        """Test UIElement construction with required fields."""
        element = UIElement(
            element_id="btn_1",
            bounds=(10, 20, 110, 120),
            text="Click Me",
            content_desc="Button description",
            class_name="android.widget.Button",
            package="com.example.app",
            clickable=True,
            visible=True,
            enabled=True,
            resource_id="com.example.app:id/btn1",
            xpath="//android.widget.Button[@text='Click Me']",
            center_x=60,
            center_y=70,
        )
        assert element.element_id == "btn_1"
        assert element.bounds == (10, 20, 110, 120)
        assert element.text == "Click Me"
        assert element.center_x == 60
        assert element.center_y == 70

    def test_center_calculation_from_bounds(self):
        """Test center_x and center_y can be derived from bounds."""
        bounds = (0, 0, 100, 200)
        expected_center_x = (0 + 100) // 2
        expected_center_y = (0 + 200) // 2

        element = UIElement(
            element_id="test",
            bounds=bounds,
            text="",
            content_desc="",
            class_name="",
            package="",
            clickable=False,
            visible=False,
            enabled=False,
            resource_id=None,
            xpath=None,
            center_x=expected_center_x,
            center_y=expected_center_y,
        )
        assert element.center_x == 50
        assert element.center_y == 100

    def test_optional_fields_can_be_none(self):
        """Test UIElement optional fields can be None."""
        element = UIElement(
            element_id="el_1",
            bounds=(0, 0, 10, 10),
            text="",
            content_desc="",
            class_name="",
            package="",
            clickable=False,
            visible=True,
            enabled=True,
            resource_id=None,
            xpath=None,
            center_x=5,
            center_y=5,
        )
        assert element.resource_id is None
        assert element.xpath is None


class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_construction_with_defaults(self):
        """Test ActionResult construction with default values."""
        result = ActionResult(
            success=True,
            action_type="click",
            target="btn1",
        )
        assert result.success is True
        assert result.action_type == "click"
        assert result.target == "btn1"
        assert result.duration_ms == 0.0
        assert result.error_message is None
        assert result.navigated_away is False
        assert result.input_text is None
        assert result.was_retried is False
        assert result.retry_count == 0
        assert result.recovery_time_ms is None
        assert result.execution_time_ms == 0.0

    def test_optional_fields(self):
        """Test ActionResult optional fields."""
        result = ActionResult(
            success=False,
            action_type="input",
            target="field1",
            duration_ms=1500.0,
            error_message="Element not found",
            navigated_away=True,
            input_text="hello",
            was_retried=True,
            retry_count=2,
            recovery_time_ms=500.0,
            execution_time_ms=2000.0,
        )
        assert result.duration_ms == 1500.0
        assert result.error_message == "Element not found"
        assert result.navigated_away is True
        assert result.input_text == "hello"
        assert result.was_retried is True
        assert result.retry_count == 2
        assert result.recovery_time_ms == 500.0
        assert result.execution_time_ms == 2000.0

    def test_success_is_required(self):
        """Test that success field is required."""
        with pytest.raises(TypeError):
            ActionResult(action_type="click", target="btn1")


class TestBoundingBox:
    """Tests for BoundingBox dataclass."""

    def test_construction(self):
        """Test BoundingBox construction."""
        box = BoundingBox(
            top_left=(10, 20),
            bottom_right=(100, 200),
        )
        assert box.top_left == (10, 20)
        assert box.bottom_right == (100, 200)

    def test_zero_coordinates(self):
        """Test BoundingBox with zero coordinates."""
        box = BoundingBox(
            top_left=(0, 0),
            bottom_right=(0, 0),
        )
        assert box.top_left == (0, 0)
        assert box.bottom_right == (0, 0)


class TestAIAction:
    """Tests for AIAction dataclass."""

    def test_construction_with_required_fields(self):
        """Test AIAction construction with required fields."""
        action = AIAction(
            action="click",
            action_desc="Click the login button",
        )
        assert action.action == "click"
        assert action.action_desc == "Click the login button"
        assert action.target_bounding_box is None
        assert action.label_id is None
        assert action.input_text is None
        assert action.reasoning == ""

    def test_construction_with_optional_fields(self):
        """Test AIAction construction with optional fields."""
        bbox = BoundingBox(top_left=(10, 20), bottom_right=(100, 200))
        action = AIAction(
            action="input",
            action_desc="Type email address",
            target_bounding_box=bbox,
            label_id=5,
            input_text="user@example.com",
            reasoning="Need to fill email field first",
        )
        assert action.target_bounding_box == bbox
        assert action.label_id == 5
        assert action.input_text == "user@example.com"
        assert action.reasoning == "Need to fill email field first"


class TestAIResponse:
    """Tests for AIResponse dataclass."""

    def test_construction(self):
        """Test AIResponse construction."""
        actions = [
            AIAction(action="click", action_desc="Click login"),
            AIAction(action="input", action_desc="Type password"),
        ]
        response = AIResponse(
            actions=actions,
            signup_completed=False,
        )
        assert len(response.actions) == 2
        assert response.signup_completed is False
        assert response.latency_ms == 0.0

    def test_construction_with_latency(self):
        """Test AIResponse construction with latency."""
        response = AIResponse(
            actions=[],
            signup_completed=True,
            latency_ms=1500.0,
        )
        assert response.latency_ms == 1500.0
        assert response.signup_completed is True

    def test_empty_actions_list(self):
        """Test AIResponse with empty actions list."""
        response = AIResponse(
            actions=[],
            signup_completed=False,
        )
        assert response.actions == []
