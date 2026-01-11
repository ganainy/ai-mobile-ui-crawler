"""Quick test to verify AI monitor data flow."""

from PySide6.QtWidgets import QApplication
from mobile_crawler.ui.widgets.ai_monitor_panel import AIMonitorPanel

def test_data_flow():
    """Test that data flows correctly through the widget."""
    app = QApplication([])
    
    panel = AIMonitorPanel()
    
    # Simulate request
    request_data = {
        "system_prompt": "You are a mobile app testing AI.",
        "user_prompt": "Analyze this screen and suggest actions."
    }
    panel.add_request(1, 1, request_data)
    
    assert panel.interactions_list.count() == 1
    print("✓ Request added successfully")
    
    # Simulate response
    response_data = {
        "success": True,
        "response": "I suggest tapping the login button.",
        "parsed_response": '{"actions": [{"action": "tap", "action_desc": "Tap login", "target_bounding_box": {"top_left": [100, 200], "bottom_right": [300, 250]}, "input_text": null, "reasoning": "User needs to login"}], "signup_completed": false}',
        "tokens_input": 150,
        "tokens_output": 75,
        "latency_ms": 1234
    }
    panel.add_response(1, 1, response_data)
    
    # Get the widget
    item = panel.interactions_list.item(0)
    widget = panel.interactions_list.itemWidget(item)
    
    # Check that data is populated
    assert widget.full_prompt == "Analyze this screen and suggest actions."
    assert widget.full_response != ""
    assert "tap" in widget.full_response.lower()
    
    print(f"✓ Response added successfully")
    print(f"✓ Prompt: {widget.full_prompt[:50]}...")
    print(f"✓ Response: {widget.full_response[:50]}...")
    print(f"✓ Parsed actions: {len(widget.parsed_actions)} action(s)")
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_data_flow()
