"""
Prompts for the ExecutorAgent.
"""

import json


def _parse_actions(action_raw: str) -> list[dict]:
    """Return the ordered actions in an Action section: one object or a JSON array."""
    candidates = []
    arr_start, arr_end = action_raw.find("["), action_raw.rfind("]")
    if arr_start != -1 and arr_end > arr_start:
        candidates.append(action_raw[arr_start : arr_end + 1])
    obj_start, obj_end = action_raw.find("{"), action_raw.rfind("}")
    if obj_start != -1 and obj_end > obj_start:
        candidates.append(action_raw[obj_start : obj_end + 1])
    for text in candidates:
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            continue
        items = value if isinstance(value, list) else [value]
        if items and all(isinstance(i, dict) for i in items):
            return items
    return []


def parse_executor_response(response: str) -> dict:
    """
    Parse the Executor LLM response.

    Extracts:
    - thought: Content between "### Thought" and "### Action"
    - action: Content between "### Action" and "### Description"
    - description: Content after "### Description"

    Args:
        response: Raw LLM response string

    Returns:
        Dictionary with 'thought', 'action', 'actions' (ordered list of action
        dicts, one per Action Batch entry) and 'description' keys
    """
    thought = (
        response.split("### Thought")[-1]
        .split("### Action")[0]
        .replace("\n", " ")
        .replace("  ", " ")
        .replace("###", "")
        .strip()
    )
    action_raw = (
        response.split("### Action")[-1]
        .split("### Description")[0]
        .replace("\n", " ")
        .replace("  ", " ")
        .replace("###", "")
        .strip()
    )
    start_idx = action_raw.find("{")
    end_idx = action_raw.rfind("}")
    if start_idx != -1 and end_idx != -1:
        action = action_raw[start_idx : end_idx + 1]
    else:
        action = action_raw
    description = response.split("### Description")[-1].replace("\n", " ").replace("  ", " ").replace("###", "").strip()

    return {
        "thought": thought,
        "action": action,
        "actions": _parse_actions(action_raw),
        "description": description,
    }
