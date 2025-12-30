#!/usr/bin/env python3
"""
AI Run Report Service

Generates AI-powered analysis reports for crawl sessions by aggregating run data
and using the configured AI model to produce structured reports.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AIRunReportService:
    """Service for generating AI-powered run reports."""
    
    def __init__(self, config):
        """
        Initialize the AI run report service.
        
        Args:
            config: Application configuration object
        """
        self.config = config
    
    def generate_ai_report(self, session_dir: Path) -> Tuple[bool, Dict[str, Any]]:
        """
        Generate an AI-powered run report for the given session.
        
        Args:
            session_dir: Path to the session directory
            
        Returns:
            Tuple of (success: bool, result: Dict)
            On success, result contains:
                - json_path: Path to JSON report file
                - markdown_path: Path to Markdown report file
            On failure, result contains:
                - error: Error message
        """
        try:
            # Find database file
            db_path = self._find_database(session_dir)
            if not db_path:
                return False, {"error": "Database file not found in session directory"}
            
            # Aggregate run data
            aggregated_data = self._aggregate_run_data(session_dir, db_path)
            if not aggregated_data:
                return False, {"error": "Failed to aggregate run data"}
            
            # Call AI model to generate report
            ai_response = self._call_ai_model(aggregated_data)
            if not ai_response:
                return False, {"error": "AI model failed to generate report"}
            
            # Parse AI response
            report_data = self._parse_ai_response(ai_response, aggregated_data)
            
            # Save reports
            json_path, markdown_path = self._save_report(report_data, session_dir)
            
            return True, {
                "json_path": str(json_path),
                "markdown_path": str(markdown_path)
            }
            
        except Exception as e:
            logger.error(f"Error generating AI run report: {e}", exc_info=True)
            return False, {"error": str(e)}
    
    def _find_database(self, session_dir: Path) -> Optional[Path]:
        """Find the database file in the session directory."""
        db_dir = session_dir / "database"
        if not db_dir.exists():
            return None
        
        # Look for .db files
        db_files = list(db_dir.glob("*.db"))
        if db_files:
            return db_files[0]
        
        return None
    
    def _aggregate_run_data(self, session_dir: Path, db_path: Path) -> Optional[Dict[str, Any]]:
        """
        Aggregate run data from multiple sources.
        
        Args:
            session_dir: Session directory path
            db_path: Database file path
            
        Returns:
            Dictionary containing aggregated run data
        """
        try:
            aggregated = {
                "session_dir": str(session_dir),
                "timestamp": datetime.now().isoformat(),
                "run_info": {},
                "steps": [],
                "errors": {"count": 0, "samples": []},
                "statistics": {},
                "log_summary": ""
            }
            
            # Connect to database
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get latest run
            cursor.execute("SELECT * FROM runs ORDER BY run_id DESC LIMIT 1")
            run_row = cursor.fetchone()
            
            if not run_row:
                conn.close()
                return None
            
            # Extract run info
            run_dict = dict(run_row)
            aggregated["run_info"] = {
                "run_id": run_dict.get("run_id"),
                "app_package": run_dict.get("app_package"),
                "start_activity": run_dict.get("start_activity"),
                "start_time": run_dict.get("start_time"),
                "end_time": run_dict.get("end_time"),
                "status": run_dict.get("status")
            }
            
            run_id = run_dict.get("run_id")
            
            # Get steps data
            cursor.execute("""
                SELECT step_number, action_description, execution_success, 
                       error_message, from_screen_id, to_screen_id,
                       ai_response_time_ms, total_tokens
                FROM steps_log
                WHERE run_id = ?
                ORDER BY step_number ASC
            """, (run_id,))
            
            steps = []
            for row in cursor.fetchall():
                step_dict = dict(row)
                steps.append({
                    "step_number": step_dict.get("step_number"),
                    "action": step_dict.get("action_description"),
                    "success": bool(step_dict.get("execution_success", False)),
                    "error": step_dict.get("error_message"),
                    "from_screen": step_dict.get("from_screen_id"),
                    "to_screen": step_dict.get("to_screen_id"),
                    "ai_response_time_ms": step_dict.get("ai_response_time_ms"),
                    "tokens": step_dict.get("total_tokens")
                })
            
            aggregated["steps"] = steps
            
            # Get error summary
            cursor.execute("""
                SELECT COUNT(*) as error_count,
                       GROUP_CONCAT(DISTINCT error_message) as error_messages
                FROM steps_log
                WHERE run_id = ? AND execution_success = 0 AND error_message IS NOT NULL
            """, (run_id,))
            
            error_row = cursor.fetchone()
            if error_row:
                error_dict = dict(error_row)
                error_count = error_dict.get("error_count", 0)
                error_messages = error_dict.get("error_messages", "")
                
                if error_count > 0:
                    # Get unique errors
                    unique_errors = []
                    if error_messages:
                        error_list = error_messages.split(',')
                        unique_errors = list(set(error_list))[:10]  # Limit to 10 unique errors
                    
                    aggregated["errors"] = {
                        "count": error_count,
                        "samples": unique_errors
                    }
            
            # Get statistics
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT step_number) as total_steps,
                    COUNT(DISTINCT CASE WHEN execution_success = 1 THEN step_number END) as successful_steps,
                    COUNT(DISTINCT CASE WHEN execution_success = 0 THEN step_number END) as failed_steps,
                    COUNT(DISTINCT to_screen_id) as unique_screens,
                    AVG(ai_response_time_ms) as avg_ai_time,
                    SUM(total_tokens) as total_tokens
                FROM steps_log
                WHERE run_id = ?
            """, (run_id,))
            
            stats_row = cursor.fetchone()
            if stats_row:
                stats_dict = dict(stats_row)
                aggregated["statistics"] = {
                    "total_steps": stats_dict.get("total_steps", 0),
                    "successful_steps": stats_dict.get("successful_steps", 0),
                    "failed_steps": stats_dict.get("failed_steps", 0),
                    "unique_screens": stats_dict.get("unique_screens", 0),
                    "avg_ai_response_time_ms": stats_dict.get("avg_ai_time"),
                    "total_tokens": stats_dict.get("total_tokens", 0)
                }
            
            conn.close()
            
            # Read log file summary
            log_file = session_dir / "logs" / "crawler.log"
            if log_file.exists():
                try:
                    # Read last 1000 lines or entire file if smaller
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        # Get last 500 lines for summary
                        log_lines = lines[-500:] if len(lines) > 500 else lines
                        aggregated["log_summary"] = "".join(log_lines)
                except Exception as e:
                    logger.warning(f"Could not read log file: {e}")
                    aggregated["log_summary"] = "Log file could not be read"
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Error aggregating run data: {e}", exc_info=True)
            return None
    
    def _call_ai_model(self, aggregated_data: Dict[str, Any]) -> Optional[str]:
        """
        Call the AI model to generate a report.
        
        Args:
            aggregated_data: Aggregated run data
            
        Returns:
            AI response text or None on failure
        """
        try:
            from domain.model_adapters import create_model_adapter
            
            # Get AI provider and model from config
            provider = self.config.get('AI_PROVIDER', 'gemini').lower()
            model_name = self.config.get('DEFAULT_MODEL_TYPE')
            
            if not model_name:
                logger.error("No AI model configured for report generation")
                return None
            
            # Get API key based on provider
            api_key = None
            if provider == 'gemini':
                api_key = self.config.get('GEMINI_API_KEY')
            elif provider == 'openrouter':
                api_key = self.config.get('OPENROUTER_API_KEY')
            elif provider == 'ollama':
                # Ollama uses base URL instead of API key
                api_key = self.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
            
            if not api_key:
                logger.error(f"API key not configured for provider: {provider}")
                return None
            
            # Create and initialize adapter
            adapter = create_model_adapter(provider, api_key, model_name)
            
            # Prepare model config
            model_config = {
                'generation_config': {
                    'temperature': 0.7,
                    'max_output_tokens': 4096
                }
            }
            
            adapter.initialize(model_config)
            
            # Build prompt
            prompt = self._build_report_prompt(aggregated_data)
            
            # Generate response
            response_text, metadata = adapter.generate_response(prompt)
            
            logger.info(f"AI report generated successfully (provider: {provider}, model: {model_name})")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error calling AI model: {e}", exc_info=True)
            return None
    
    def _build_report_prompt(self, aggregated_data: Dict[str, Any]) -> str:
        """
        Build the prompt for AI report generation.
        
        Args:
            aggregated_data: Aggregated run data
            
        Returns:
            Formatted prompt string
        """
        run_info = aggregated_data.get("run_info", {})
        stats = aggregated_data.get("statistics", {})
        steps = aggregated_data.get("steps", [])
        errors = aggregated_data.get("errors", {})
        
        # Ensure errors is a dictionary (handle edge cases)
        if not isinstance(errors, dict):
            errors = {"count": 0, "samples": []}
        
        prompt = f"""You are analyzing a mobile app crawling session. Generate a comprehensive run report in JSON format.

SESSION INFORMATION:
- App Package: {run_info.get('app_package', 'Unknown')}
- Start Activity: {run_info.get('start_activity', 'Unknown')}
- Start Time: {run_info.get('start_time', 'Unknown')}
- End Time: {run_info.get('end_time', 'Unknown')}
- Status: {run_info.get('status', 'Unknown')}

STATISTICS:
- Total Steps: {stats.get('total_steps', 0)}
- Successful Steps: {stats.get('successful_steps', 0)}
- Failed Steps: {stats.get('failed_steps', 0)}
- Unique Screens Discovered: {stats.get('unique_screens', 0)}
- Average AI Response Time: {stats.get('avg_ai_response_time_ms', 0):.2f} ms
- Total Tokens Used: {stats.get('total_tokens', 0)}

ERRORS ENCOUNTERED:
"""
        
        if errors.get('count', 0) > 0:
            prompt += f"- Total Errors: {errors.get('count', 0)}\n"
            prompt += "- Sample Error Messages:\n"
            for error in errors.get('samples', [])[:5]:
                prompt += f"  * {error}\n"
        else:
            prompt += "- No errors encountered\n"
        
        prompt += f"""

RECENT STEPS (last 20):
"""
        for step in steps[-20:]:
            status = "✓" if step.get('success') else "✗"
            prompt += f"Step {step.get('step_number')}: {status} {step.get('action', 'Unknown action')}\n"
            if step.get('error'):
                prompt += f"  Error: {step.get('error')}\n"
        
        prompt += """

Generate a JSON report with the following structure:
{
  "executive_summary": "High-level overview of the crawl session",
  "what_went_well": [
    "List of successful aspects"
  ],
  "issues_encountered": [
    "List of problems, errors, or failures"
  ],
  "root_causes": [
    "Analysis of underlying causes (where identifiable)"
  ],
  "mitigation_steps": [
    "Recommendations and actionable steps to address issues"
  ],
  "non_mitigatable_issues": [
    "Explicit indication when issues cannot be mitigated (if any)"
  ],
  "statistics_summary": "Summary of key metrics and performance indicators"
}

IMPORTANT: Return ONLY valid JSON. Do not include markdown formatting, code blocks, or any other text outside the JSON structure.
"""
        
        return prompt
    
    def _parse_ai_response(self, ai_response: str, aggregated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the AI response into structured report data.
        
        Args:
            ai_response: Raw AI response text
            aggregated_data: Original aggregated data
            
        Returns:
            Structured report dictionary
        """
        try:
            # Try to extract JSON from response (handle cases where AI wraps JSON in markdown)
            response_text = ai_response.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                # Find the first newline after ```
                first_newline = response_text.find("\n")
                if first_newline != -1:
                    response_text = response_text[first_newline + 1:]
                # Remove trailing ```
                if response_text.endswith("```"):
                    response_text = response_text[:-3].strip()
            
            # Try to find JSON object
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start != -1 and json_end > json_start:
                response_text = response_text[json_start:json_end]
            
            # Parse JSON
            report_data = json.loads(response_text)
            
            # Validate structure
            required_keys = [
                "executive_summary", "what_went_well", "issues_encountered",
                "root_causes", "mitigation_steps", "non_mitigatable_issues"
            ]
            
            for key in required_keys:
                if key not in report_data:
                    report_data[key] = [] if key.endswith("s") else ""
            
            # Add metadata
            report_data["metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "session_dir": aggregated_data.get("session_dir"),
                "run_id": aggregated_data.get("run_info", {}).get("run_id"),
                "app_package": aggregated_data.get("run_info", {}).get("app_package")
            }
            
            # Add statistics
            report_data["statistics"] = aggregated_data.get("statistics", {})
            
            return report_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"AI response was: {ai_response[:500]}")
            
            # Return a fallback report structure
            return {
                "executive_summary": "Report generation completed but AI response could not be parsed as JSON.",
                "what_went_well": [],
                "issues_encountered": ["AI response parsing failed"],
                "root_causes": ["AI model returned invalid JSON format"],
                "mitigation_steps": ["Review AI model configuration and prompt structure"],
                "non_mitigatable_issues": [],
                "statistics_summary": "See statistics section",
                "statistics": aggregated_data.get("statistics", {}),
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "parse_error": str(e),
                    "raw_response_preview": ai_response[:200]
                }
            }
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}", exc_info=True)
            return {
                "executive_summary": "Error occurred during report generation.",
                "what_went_well": [],
                "issues_encountered": [f"Report parsing error: {str(e)}"],
                "root_causes": [],
                "mitigation_steps": [],
                "non_mitigatable_issues": [],
                "statistics_summary": "",
                "statistics": aggregated_data.get("statistics", {}),
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "error": str(e)
                }
            }
    
    def _save_report(self, report_data: Dict[str, Any], session_dir: Path) -> Tuple[Path, Path]:
        """
        Save the report in both JSON and Markdown formats.
        
        Args:
            report_data: Structured report data
            session_dir: Session directory path
            
        Returns:
            Tuple of (json_path, markdown_path)
        """
        # Create ai_reports directory
        reports_dir = session_dir / "ai_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        
        # Save JSON
        json_path = reports_dir / f"ai_run_report_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # Generate and save Markdown
        markdown_path = reports_dir / f"ai_run_report_{timestamp}.md"
        markdown_content = self._generate_markdown(report_data)
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return json_path, markdown_path
    
    def _generate_markdown(self, report_data: Dict[str, Any]) -> str:
        """
        Generate Markdown format from report data.
        
        Args:
            report_data: Structured report data
            
        Returns:
            Markdown formatted string
        """
        md = "# AI-Generated Run Report\n\n"
        
        # Metadata
        metadata = report_data.get("metadata", {})
        md += f"**Generated:** {metadata.get('generated_at', 'Unknown')}\n"
        md += f"**App Package:** {metadata.get('app_package', 'Unknown')}\n"
        md += f"**Run ID:** {metadata.get('run_id', 'Unknown')}\n\n"
        
        # Executive Summary
        md += "## Executive Summary\n\n"
        md += f"{report_data.get('executive_summary', 'No summary provided.')}\n\n"
        
        # What Went Well
        md += "## What Went Well\n\n"
        what_went_well = report_data.get("what_went_well", [])
        if what_went_well:
            for item in what_went_well:
                md += f"- {item}\n"
        else:
            md += "*No specific successes identified.*\n"
        md += "\n"
        
        # Issues Encountered
        md += "## Issues Encountered\n\n"
        issues = report_data.get("issues_encountered", [])
        if issues:
            for issue in issues:
                md += f"- {issue}\n"
        else:
            md += "*No issues identified.*\n"
        md += "\n"
        
        # Root Causes
        md += "## Root Causes\n\n"
        root_causes = report_data.get("root_causes", [])
        if root_causes:
            for cause in root_causes:
                md += f"- {cause}\n"
        else:
            md += "*No root causes identified.*\n"
        md += "\n"
        
        # Mitigation Steps
        md += "## Mitigation Steps\n\n"
        mitigations = report_data.get("mitigation_steps", [])
        if mitigations:
            for step in mitigations:
                md += f"- {step}\n"
        else:
            md += "*No mitigation steps provided.*\n"
        md += "\n"
        
        # Non-Mitigatable Issues
        md += "## Non-Mitigatable Issues\n\n"
        non_mitigatable = report_data.get("non_mitigatable_issues", [])
        if non_mitigatable:
            for issue in non_mitigatable:
                md += f"- {issue}\n"
        else:
            md += "*No non-mitigatable issues identified.*\n"
        md += "\n"
        
        # Statistics
        md += "## Statistics\n\n"
        stats = report_data.get("statistics", {})
        if stats:
            md += f"- **Total Steps:** {stats.get('total_steps', 0)}\n"
            md += f"- **Successful Steps:** {stats.get('successful_steps', 0)}\n"
            md += f"- **Failed Steps:** {stats.get('failed_steps', 0)}\n"
            md += f"- **Unique Screens:** {stats.get('unique_screens', 0)}\n"
            if stats.get('avg_ai_response_time_ms'):
                md += f"- **Average AI Response Time:** {stats.get('avg_ai_response_time_ms', 0):.2f} ms\n"
            if stats.get('total_tokens'):
                md += f"- **Total Tokens Used:** {stats.get('total_tokens', 0)}\n"
        else:
            md += "*No statistics available.*\n"
        md += "\n"
        
        # Statistics Summary (if provided by AI)
        stats_summary = report_data.get("statistics_summary")
        if stats_summary:
            md += "## Statistics Summary\n\n"
            md += f"{stats_summary}\n\n"
        
        return md

