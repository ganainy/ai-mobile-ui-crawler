---
name: debug-skill
description: Performs deep technical analysis of issues and generates a structured report with a fix plan, without implementing changes.
---

# Debug Skill: Analysis & Reporting

This skill is designed for deep investigation and diagnostic reporting. It prioritizes understanding the root cause and planning a solution over immediate implementation.

## When to use this skill
- When a bug or issue is reported but the solution is not immediately obvious.
- When the user explicitly asks for a "debug report" or "analysis" before proceeding with changes.
- When you need to de-risk a complex change by planning it out first.

## Constraints
- **CRITICAL**: Do NOT modify any source code or project files while using this skill.
- **CRITICAL**: Your output must be a comprehensive report saved to a new `.md` file.

## How to use it

### 1. Investigation Phase
Use the available tools to gather context:
- `grep_search`: Find relevant error messages or code patterns.
- `view_file` / `view_file_outline`: Understand the structure and logic of the affected components.
- `run_command`: Execute tests or reproduction scripts to observe the failure (e.g., `pytest`, `npm test`).
- `list_dir`: Check for logs, screenshots, or generated artifacts that might contain clues.

### 2. Diagnosis Phase
Analyze the gathered data to identify:
- The exact point of failure.
- The state of the system leading up to the failure.
- Why the current code is producing the incorrect behavior.

### 3. Reporting Phase
Create a new markdown file for the report:
- **Location**: `.agent/reports/debug_report_YYYYMMDD_HHMMSS.md` (use current timestamp)
- **File Creation**: Use the `write_to_file` tool to create the report file.

The report file should follow this template:

---
## 🔍 Debug Report

### 1. Problem Description
- **Symptoms**: What is the observable failure?
- **Context**: Under what conditions does it occur?

### 2. Root Cause Analysis
- **Location**: Which file(s) and line(s) are responsible?
- **Analysis**: Explain *why* it is broken. Trace the logic or data flow that leads to the error.

### 3. Proposed Fix
- **Strategy**: High-level explanation of the fix.
- **Step-by-Step Plan**:
    1. [ ] Action 1 (e.g., Modify `class.method` to handle `None`)
    2. [ ] Action 2 (e.g., Update test case to verify fix)
- **Potential Side Effects**: What else might this change impact?

### 4. Verification Plan
- How should the fix be tested once implemented?
---

## Rules of Engagement
1. Be extremely thorough in the "Root Cause Analysis".
2. Ensure the "Proposed Fix" is implementation-ready (specific line numbers or code snippets in the report are encouraged).
3. If multiple solutions exist, compare them and recommend the best one.
4. Stop after providing the report and wait for user approval to proceed with implementation (if applicable).
