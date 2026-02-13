# AI Action Schema

**Protocol**: JSON
**Direction**: VLM -> Crawler

The VLM must respond with a JSON object conforming to this schema.

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "actions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "action": {
            "type": "string",
            "enum": ["click", "input", "long_press", "scroll_up", "scroll_down", "scroll_left", "scroll_right", "back"]
          },
          "action_desc": {
            "type": "string"
          },
          "target_bounding_box": {
            "type": "object",
            "properties": {
              "top_left": {
                "type": "array",
                "items": { "type": "integer" },
                "minItems": 2,
                "maxItems": 2
              },
              "bottom_right": {
                "type": "array",
                "items": { "type": "integer" },
                "minItems": 2,
                "maxItems": 2
              }
            },
            "required": ["top_left", "bottom_right"]
          },
          "input_text": {
            "type": "string"
          },
          "reasoning": {
            "type": "string"
          }
        },
        "required": ["action", "action_desc", "target_bounding_box", "reasoning"]
      }
    },
    "signup_completed": {
      "type": "boolean"
    }
  },
  "required": ["actions", "signup_completed"]
}
```
