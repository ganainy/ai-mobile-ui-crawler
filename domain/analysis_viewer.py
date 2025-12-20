# analysis_viewer.py
import base64
import json
import logging
import os
import sqlite3
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(asctime)s %(module)s: %(message)s')

try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False
    pisa = None


class RunAnalyzer:
    def __init__(self, db_path: str, output_data_dir: str, app_package_for_run: Optional[str] = None):
        self.db_path = db_path
        self.output_data_dir = output_data_dir
        self.app_package_for_run = app_package_for_run
        self.conn: Optional[sqlite3.Connection] = None

        if not os.path.exists(self.db_path):
            logger.error(f"Database file not found: {self.db_path}")
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        
        self._connect_db()

    def _connect_db(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row 
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database {self.db_path}: {e}")
            self.conn = None
            raise

    def _close_db_connection(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def list_runs(self) -> Dict[str, Any]:
        """
        Get a list of all runs in the database.
        
        Returns:
            Dictionary containing:
            - success: bool indicating if operation was successful
            - runs: list of run dictionaries
            - message: optional message for display
        """
        result = {
            "success": False,
            "runs": [],
            "message": ""
        }
        
        if not self.conn:
            logger.error("No database connection available to list runs.")
            self._connect_db()
            if not self.conn:
                result["message"] = "Failed to connect to database"
                return result

        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT run_id, app_package, start_activity, start_time, end_time, status FROM runs ORDER BY run_id DESC")
            runs = cursor.fetchall()
            result["success"] = True
        except sqlite3.Error as e:
            logger.error(f"Error fetching runs from database: {e}")
            self._close_db_connection()
            result["message"] = f"Error fetching runs: {e}"
            return result

        if not runs:
            result["message"] = "No runs found in the database."
        else:
            for run_item in runs:
                start_time_str = run_item['start_time'][:19] if run_item['start_time'] else "N/A"
                result["runs"].append({
                    "run_id": run_item['run_id'],
                    "app_package": run_item['app_package'],
                    "start_activity": run_item['start_activity'],
                    "start_time": start_time_str,
                    "status": run_item['status']
                })
        
        self._close_db_connection()
        return result

    def _get_screenshot_full_path(self, db_screenshot_path: Optional[str]) -> Optional[str]:
        if not db_screenshot_path:
            return None
        
        if os.path.isabs(db_screenshot_path):
            if os.path.exists(db_screenshot_path):
                return os.path.abspath(db_screenshot_path)
            else:
                logger.warning(f"Absolute screenshot path from DB does not exist: '{db_screenshot_path}'")
                if self.output_data_dir and self.app_package_for_run:
                    potential_path_rel = os.path.join(self.output_data_dir, "screenshots", f"crawl_screenshots_{self.app_package_for_run}", os.path.basename(db_screenshot_path))
                    if os.path.exists(potential_path_rel):
                        return os.path.abspath(potential_path_rel)
                return None

        if self.output_data_dir and self.app_package_for_run:
            potential_path = os.path.join(self.output_data_dir, "screenshots", f"crawl_screenshots_{self.app_package_for_run}", os.path.basename(db_screenshot_path))
            if os.path.exists(potential_path):
                 return os.path.abspath(potential_path)
            else:
                potential_path_flat = os.path.join(self.output_data_dir, "screenshots", db_screenshot_path)
                if os.path.exists(potential_path_flat):
                    return os.path.abspath(potential_path_flat)

        logger.warning(f"Screenshot path '{db_screenshot_path}' could not be reliably resolved to an existing absolute path. PDF generation might fail for this image.")
        return None
    
    def _calculate_summary_metrics(self, run_id: int, run_data: sqlite3.Row, steps: List[sqlite3.Row]) -> Dict[str, Any]:
        """Calculates all the summary metrics for a given run."""
        metrics = {}
        total_steps = len(steps)
        
        # General Run Info
        if run_data['start_time'] and run_data['end_time']:
            start = datetime.fromisoformat(run_data['start_time'])
            end = datetime.fromisoformat(run_data['end_time'])
            duration = end - start
            metrics['Total Duration'] = str(duration).split('.')[0]
        else:
            metrics['Total Duration'] = "N/A (Run Incomplete)"

        metrics['Final Status'] = run_data['status']
        metrics['Total Steps'] = total_steps
        
        # Coverage Metrics
        unique_screen_ids = {s['from_screen_id'] for s in steps if s['from_screen_id']} | {s['to_screen_id'] for s in steps if s['to_screen_id']}
        metrics['Unique Screens Discovered'] = len(unique_screen_ids)
        
        unique_transitions = {(s['from_screen_id'], s['to_screen_id'], s['action_description']) for s in steps}
        metrics['Unique Transitions'] = len(unique_transitions)
        
        if self.conn and unique_screen_ids:
            cursor = self.conn.cursor()
            placeholders = ','.join('?' for _ in unique_screen_ids)
            query = f"SELECT COUNT(DISTINCT activity_name) FROM screens WHERE screen_id IN ({placeholders})"
            cursor.execute(query, list(unique_screen_ids))
            metrics['Activity Coverage'] = cursor.fetchone()[0]
        else:
            metrics['Activity Coverage'] = "N/A"

        action_types = [json.loads(s['ai_suggestion_json']).get('action') for s in steps if s['ai_suggestion_json']]
        action_distribution = {action: action_types.count(action) for action in set(action_types) if action}
        metrics['Action Distribution'] = ", ".join([f"{k}: {v}" for k, v in action_distribution.items()])

        # Efficiency Metrics
        if metrics['Unique Screens Discovered'] > 0:
            metrics['Steps per New Screen'] = f"{total_steps / metrics['Unique Screens Discovered']:.2f}"
        else:
            metrics['Steps per New Screen'] = "N/A"
            
        total_tokens = sum(s['total_tokens'] for s in steps if s['total_tokens'])
        metrics['Total Token Usage'] = f"{total_tokens:,}" if total_tokens else "N/A"
        
        valid_response_times = [s['ai_response_time_ms'] for s in steps if s['ai_response_time_ms'] is not None]
        if valid_response_times:
            avg_time = sum(valid_response_times) / len(valid_response_times)
            metrics['Avg AI Response Time'] = f"{avg_time:.0f} ms"
        else:
            metrics['Avg AI Response Time'] = "N/A"
        
        valid_element_find_times = [s['element_find_time_ms'] for s in steps if 'element_find_time_ms' in s.keys() and s['element_find_time_ms'] is not None]
        if valid_element_find_times:
            avg_element_time = sum(valid_element_find_times) / len(valid_element_find_times)
            metrics['Avg Element Find Time'] = f"{avg_element_time:.0f} ms"
        else:
            metrics['Avg Element Find Time'] = "N/A"
            
        # Robustness Metrics
        stuck_steps = sum(1 for s in steps if s['from_screen_id'] == s['to_screen_id'])
        metrics['Stuck Steps (No-Op)'] = stuck_steps
        
        exec_failures = sum(1 for s in steps if not s['execution_success'])
        metrics['Execution Failures'] = exec_failures
        
        if total_steps > 0:
            metrics['Action Success Rate'] = f"{(1 - (exec_failures / total_steps)) * 100:.1f}%"
        else:
            metrics['Action Success Rate'] = "N/A"
            
        return metrics

    def _generate_error_summary_html(self, steps: List[sqlite3.Row]) -> str:
        """Generates an HTML table for failed steps."""
        failed_steps = [s for s in steps if not s['execution_success']]
        if not failed_steps:
            return ""
            
        html_parts = ["""
        <div class="summary-section error-section">
            <h2 style="color: #dc3545; border-bottom-color: #dc3545;">⚠️ Issues Found</h2>
            <table class="summary-table">
                <thead>
                    <tr>
                        <th style="width: 10%">Step</th>
                        <th style="width: 20%">Action</th>
                        <th style="width: 70%">Error Message</th>
                    </tr>
                </thead>
                <tbody>
        """]
        
        for step in failed_steps:
            action_desc = escape(step['action_description'] or 'N/A')
            error_msg = escape(step['error_message'] or 'Unknown error')
            html_parts.append(f"""
                <tr>
                    <td style="text-align: center; font-weight: bold;">{step['step_number']}</td>
                    <td>{action_desc}</td>
                    <td style="color: #dc3545;">{error_msg}</td>
                </tr>
            """)
            
        html_parts.append("</tbody></table></div>")
        return "".join(html_parts)

    def _generate_summary_table_html(self, metrics: Dict[str, Any]) -> str:
        """Generates a modern HTML summary section."""
        
        # Helper for metrics rows
        def metric_row(label, value):
             return f"<tr><td>{label}</td><td style='text-align: right; font-weight: 600;'>{value}</td></tr>"

        html = f"""
        <div class="summary-container">
            <!-- General Info Card -->
            <div class="card">
                <div class="card-header">General Information</div>
                <div class="card-body">
                    <table class="metrics-table">
                         {metric_row('Total Duration', metrics.get('Total Duration', 'N/A'))}
                         {metric_row('Total Steps', metrics.get('Total Steps', 'N/A'))}
                         {metric_row('Final Status', metrics.get('Final Status', 'N/A'))}
                    </table>
                </div>
            </div>
            
            <!-- Coverage Card -->
            <div class="card">
                <div class="card-header">Coverage</div>
                <div class="card-body">
                    <table class="metrics-table">
                         {metric_row('Screens Discovered', metrics.get('Unique Screens Discovered', 'N/A'))}
                         {metric_row('Unique Transitions', metrics.get('Unique Transitions', 'N/A'))}
                         {metric_row('Activity Coverage', metrics.get('Activity Coverage', 'N/A'))}
                    </table>
                </div>
            </div>
            
            <!-- Efficiency & Robustness Card -->
            <div class="card">
                 <div class="card-header">Performance & Health</div>
                 <div class="card-body">
                    <table class="metrics-table">
                         {metric_row('Avg AI Response', metrics.get('Avg AI Response Time', 'N/A'))}
                         {metric_row('Success Rate', metrics.get('Action Success Rate', 'N/A'))}
                         {metric_row('Execution Failures', metrics.get('Execution Failures', '0'))}
                    </table>
                 </div>
            </div>
        </div>
        """
        return html

    def _fetch_run_and_steps_data(self, run_id: int) -> Tuple[Optional[sqlite3.Row], Optional[List[sqlite3.Row]]]:
        if not self.conn:
            logger.error(f"No database connection to fetch data for run {run_id}.")
            self._connect_db()
            if not self.conn:
                return None, None
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            run_data = cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error fetching run data for run_id {run_id}: {e}")
            return None, None

        if not run_data:
            return None, None

        if not self.app_package_for_run and run_data['app_package']:
            self.app_package_for_run = run_data['app_package']
        
        query = """
        SELECT sl.*,
               s_from.screenshot_path AS from_screenshot_path, s_from.activity_name AS from_activity_name, s_from.composite_hash AS from_hash,
               s_to.screenshot_path AS to_screenshot_path, s_to.activity_name AS to_activity_name, s_to.composite_hash AS to_hash
        FROM steps_log sl
        LEFT JOIN screens s_from ON sl.from_screen_id = s_from.screen_id
        LEFT JOIN screens s_to ON sl.to_screen_id = s_to.screen_id
        WHERE sl.run_id = ? ORDER BY sl.step_number ASC
        """
        try:
            cursor.execute(query, (run_id,))
            steps = cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error fetching steps for run_id {run_id}: {e}")
            return run_data, None
        
        return run_data, steps

    def _image_to_base64(self, image_path: str) -> Optional[str]:
        if not os.path.exists(image_path):
            logger.warning(f"Cannot encode image to base64: File not found at {image_path}")
            return None
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            image_type = Path(image_path).suffix.lower().lstrip('.')
            if image_type == 'jpg': image_type = 'jpeg'
            if image_type not in ['jpeg', 'png', 'gif']: image_type = 'png' 
            return f"data:image/{image_type};base64,{encoded_string}"
        except Exception as e:
            logger.error(f"Error encoding image {image_path} to base64: {e}", exc_info=True)
            return None

    def _clean_and_format_json(self, json_str: Optional[str]) -> str:
        """Cleans, formats, and syntax-highlights JSON string."""
        if not json_str:
            return ""
            
        # 1. Clean Markdown
        clean_str = json_str.strip()
        if clean_str.startswith("```json"): clean_str = clean_str[7:]
        if clean_str.startswith("```"): clean_str = clean_str[3:]
        if clean_str.endswith("```"): clean_str = clean_str[:-3]
        clean_str = clean_str.strip()
        
        try:
            # 2. Parse
            data = json.loads(clean_str)
            
            # 3. Pretty Print
            pretty = json.dumps(data, indent=2)
            
            # 4. Colorize (Simple Regex-free approach for safety)
            # We escape everything first, then wrap known structures
            lines = pretty.split('\n')
            colored_lines = []
            
            for line in lines:
                # Basic heuristic highlighting
                escaped_line = escape(line)
                
                # Highlight Keys: "key":
                if '"' in escaped_line and ':' in escaped_line:
                    # Very naive but robust enough for simple JSON: color the part before the first colon
                    parts = escaped_line.split(':', 1)
                    key_part = parts[0]
                    val_part = parts[1]
                    
                    # Color key in Blue
                    # Note: key_part includes spaces/indentation, we want to color the "key"
                    if '"' in key_part:
                        key_part = key_part.replace('"', '<span style="color: #2980b9;">"').replace('"', '"</span>', 1) # Close spans manually is tricky with replace
                        # Simpler: just wrap the whole key string
                        key_start = key_part.find('"')
                        key_end = key_part.rfind('"')
                        if key_start != -1 and key_end != -1:
                           key_text = key_part[key_start:key_end+1]
                           colored_key = f'<span style="color: #2980b9;">{key_text}</span>'
                           key_part = key_part[:key_start] + colored_key + key_part[key_end+1:]
                           
                    # Color String Values in Green
                    if '"' in val_part:
                        # Find the string value
                        v_start = val_part.find('"')
                        v_end = val_part.rfind('"')
                        if v_start != -1 and v_end != -1 and v_end > v_start:
                             val_text = val_part[v_start:v_end+1]
                             colored_val = f'<span style="color: #27ae60;">{val_text}</span>'
                             val_part = val_part[:v_start] + colored_val + val_part[v_end+1:]
                    
                    # Color null/true/false in Orange
                    for kw in ['null', 'true', 'false']:
                        if kw in val_part:
                            val_part = val_part.replace(kw, f'<span style="color: #d35400; font-weight: bold;">{kw}</span>')

                    escaped_line = key_part + ':' + val_part
                    
                colored_lines.append(escaped_line)
                
            final_html = "\n".join(colored_lines)
            return f"<pre>{final_html}</pre>"
            
        except json.JSONDecodeError:
            # Fallback for invalid JSON
            return f"<pre>{escape(json_str)}</pre>"

    def analyze_run_to_pdf(self, run_id: int, pdf_filepath: str) -> Dict[str, Any]:
        """
        Generate PDF report for a run.
        """
        result = {
            "success": False,
            "pdf_path": None,
            "error": None
        }
        
        if not XHTML2PDF_AVAILABLE:
            error_msg = "xhtml2pdf library is not installed. Cannot generate PDF. Please install it using: pip install xhtml2pdf"
            logger.error(error_msg)
            result["error"] = error_msg
            self._close_db_connection()
            return result

        run_data, steps = self._fetch_run_and_steps_data(run_id)

        if not run_data:
            error_msg = f"Run ID {run_id} not found. PDF will not be generated."
            result["error"] = error_msg
            self._close_db_connection()
            return result

        steps = steps or []
        metrics_data = self._calculate_summary_metrics(run_id, run_data, steps)
        
        # Determine max response time for bar charts
        max_response_time = 1.0
        if steps:
            times = [s['ai_response_time_ms'] for s in steps if s['ai_response_time_ms'] is not None]
            if times:
                max_response_time = max(times) or 1.0

        summary_table_html = self._generate_summary_table_html(metrics_data)
        error_summary_html = self._generate_error_summary_html(steps)
        
        html_parts = ["""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Run Analysis Report</title>
            <style>
                @page { 
                    size: a4 portrait; 
                    margin: 0.5in; 
                }
                body { font-family: 'Helvetica', 'Arial', sans-serif; margin: 0; font-size: 9pt; line-height: 1.4; color: #333; }
                
                h1 { font-size: 18pt; text-align: center; color: #2c3e50; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; } 
                h2 { font-size: 14pt; color: #2c3e50; margin-top: 25px; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 5px; } 
                h3 { font-size: 11pt; margin-top: 0; margin-bottom: 10px; color: #fff; background-color: #34495e; padding: 6px 10px; border-radius: 4px 4px 0 0; }
                h4 { font-size: 8pt; text-transform: uppercase; letter-spacing: 0.5px; color: #7f8c8d; margin-top: 10px; margin-bottom: 4px; border-bottom: none; }
                
                /* Summary Cards */
                .summary-container { display: -pdf-flex-box; -pdf-justify-content: space-between; margin-bottom: 20px; }
                .card { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 5px; padding: 0; width: 32%; display: inline-block; vertical-align: top; margin-right: 1%; }
                .card-header { background: #e9ecef; padding: 5px 10px; font-weight: bold; color: #495057; font-size: 8.5pt; border-bottom: 1px solid #dee2e6; }
                .card-body { padding: 8px; }
                .metrics-table { width: 100%; font-size: 8pt; }
                .metrics-table td { padding: 2px 0; }

                /* Error Table */
                .summary-table { width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-bottom: 20px; }
                .summary-table th { background: #f8f9fa; text-align: left; padding: 8px; border-bottom: 2px solid #dee2e6; color: #495057; font-weight: 600; }
                .summary-table td { padding: 8px; border-bottom: 1px solid #dee2e6; vertical-align: top; }

                /* Step Container */
                .step-container { 
                    margin-bottom: 15px; 
                    border: 1px solid #e0e0e0; 
                    border-radius: 4px;
                    background-color: #fff;
                    page-break-inside: avoid;
                    box-shadow: 1px 1px 3px rgba(0,0,0,0.05);
                }
                
                .step-content { padding: 10px; display: -pdf-flex-box; -pdf-flex-direction: row; }
                .step-info { width: 55%; padding-right: 15px; display: inline-block; vertical-align: top; }
                .step-visuals { width: 40%; display: inline-block; vertical-align: top; }
                
                /* Features */
                .feature-row { margin-bottom: 4px; font-size: 8.5pt; }
                .feature-label { font-weight: bold; color: #555; font-size: 8pt; display: inline-block; width: 80px; }
                
                /* Badges */
                .badge { padding: 2px 6px; border-radius: 10px; font-size: 7.5pt; font-weight: bold; color: #fff; display: inline-block; }
                .badge-success { background-color: #28a745; }
                .badge-failure { background-color: #dc3545; }
                .badge-action { background-color: #17a2b8; }
                
                /* Code / Pre */
                pre { 
                    background-color: #f4f6f7; 
                    border: 1px solid #dcdde1; 
                    border-radius: 3px; 
                    padding: 8px; 
                    font-family: 'Courier New', Courier, monospace; 
                    font-size: 7.5pt; 
                    color: #2c3e50; 
                    white-space: pre-wrap; 
                    word-wrap: break-word;
                    overflow: hidden;
                    margin-top: 2px;
                }
                
                /* Screenshots Table Layout */
                .screenshots-table { width: 100%; border-collapse: collapse; margin-top: 5px; }
                .screenshots-table td { vertical-align: middle; text-align: center; padding: 2px; }
                .screenshot-cell { width: 45%; }
                .arrow-cell { width: 10%; font-size: 20pt; color: #bdc3c7; }
                
                .screenshot { 
                    width: auto;
                    max-width: 98%; 
                    height: auto; 
                    max-height: 220px;
                    border: 1px solid #ddd; 
                    background: #fff;
                    box-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                }
                .screenshot-label { font-size: 7pt; color: #7f8c8d; margin-top: 3px; display: block; font-weight: bold; }

                /* Bar Chart (HTML CSS) */
                .bar-container { background-color: #f1f1f1; height: 6px; width: 100px; border-radius: 3px; display: inline-block; vertical-align: middle; margin-left: 5px; }
                .bar-fill { height: 100%; border-radius: 3px; background-color: #3498db; }
                
            </style>
        </head>
        <body>
        """]

        # Header with App Name and Date
        run_date = "N/A"
        if run_data['start_time']:
             try:
                run_date = datetime.fromisoformat(run_data['start_time']).strftime("%Y-%m-%d %H:%M")
             except: pass
             
        html_parts.append(f"""
        <h1>Analysis Report: {escape(str(run_data['app_package']))}</h1>
        <p style="text-align: center; color: #777; margin-top: -15px; margin-bottom: 25px;">
            Run ID: {run_id} &bull; Date: {run_date}
        </p>
        """)

        html_parts.append(summary_table_html)
        html_parts.append(error_summary_html)
        
        if not steps:
            html_parts.append("<div class='step-container'><div class='step-content'><p>No steps found for this run.</p></div></div>")
        else:
            html_parts.append("<h2>Execution Timeline</h2>")
            for step in steps:
                step_num = step['step_number']
                
                # --- Prepare Step Data ---
                action_desc = escape(step['action_description'] or 'N/A')
                from_activity = escape(step['from_activity_name'] or 'Unknown')
                
                # Status Badge
                if step['execution_success']:
                    status_badge = "<span class='badge badge-success'>SUCCESS</span>"
                else:
                    status_badge = "<span class='badge badge-failure'>FAILED</span>"

                # AI Time Bar Chart
                ai_time_html = ""
                if step['ai_response_time_ms']:
                    sec = step['ai_response_time_ms'] / 1000.0
                    pct = min(100, int((step['ai_response_time_ms'] / max_response_time) * 100))
                    bar_color = "#3498db"
                    if pct > 80: bar_color = "#e67e22" # Orange for slow
                    ai_time_html = f"""
                    <div class='feature-row'>
                        <span class='feature-label'>AI Time:</span> {sec:.2f}s
                        <div class='bar-container'><div class='bar-fill' style='width: {pct}%; background-color: {bar_color};'></div></div>
                    </div>
                    """
                
                # AI Suggestion parsing
                ai_sugg_html = self._clean_and_format_json(step['ai_suggestion_json'])

                # Error Message if any
                error_html = ""
                if not step['execution_success'] and step['error_message']:
                    error_html = f"""
                    <div style='margin-top: 8px; padding: 5px; background: #fff5f5; border-left: 3px solid #dc3545; color: #dc3545; font-size: 8pt;'>
                        <strong>Error:</strong> {escape(step['error_message'])}
                    </div>
                    """

                # Screenshots Table Construction
                screenshots_html = ""
                img_from = self._get_screenshot_full_path(step['from_screenshot_path'])
                img_to = self._get_screenshot_full_path(step['to_screenshot_path'])
                
                b64_from = self._image_to_base64(img_from) if img_from else None
                b64_to = self._image_to_base64(img_to) if img_to else None
                
                if b64_from or b64_to:
                    # Use a table for reliable side-by-side layout in PDF
                    row_content = ""
                    
                    if b64_from:
                        row_content += f"""
                        <td class='screenshot-cell'>
                            <img src='{b64_from}' class='screenshot'><br>
                            <span class='screenshot-label'>FROM: {from_activity}</span>
                        </td>
                        """
                    else:
                        row_content += "<td class='screenshot-cell'></td>"
                        
                    if b64_from and b64_to:
                        row_content += "<td class='arrow-cell'>&rarr;</td>"
                    elif b64_to: # If only TO exists, add empty arrow cell for spacing? No, just skip.
                        pass

                    if b64_to:
                        row_content += f"""
                        <td class='screenshot-cell'>
                            <img src='{b64_to}' class='screenshot'><br>
                            <span class='screenshot-label'>TO: {escape(step['to_activity_name'] or 'Unknown')}</span>
                        </td>
                        """
                    else:
                        row_content += "<td class='screenshot-cell'></td>"
                        
                    screenshots_html = f"<table class='screenshots-table'><tr>{row_content}</tr></table>"

                # Step HTML Construction
                html_parts.append(f"""
                <div class='step-container'>
                    <h3>Step {step_num} {status_badge}</h3>
                    <div class='step-content'>
                        <div class='step-info'>
                            <div class='feature-row'><span class='feature-label'>Action:</span> {action_desc}</div>
                            {ai_time_html}
                            <h4 style="margin-top: 10px;">AI Reasoning & Input</h4>
                            {ai_sugg_html}
                            {error_html}
                        </div>
                        <div class='step-visuals'>
                             {screenshots_html}
                        </div>
                    </div>
                </div>
                """)
        
        html_parts.append("</body></html>")
        full_html = "".join(html_parts)

        # --- MODIFIED: More robust PDF generation block ---
        try:
            with open(pdf_filepath, "wb") as f_pdf:
                if pisa:
                    # pisa.CreatePDF returns a pisaDocument status object
                    pisa_status = pisa.CreatePDF(full_html, dest=f_pdf, encoding='utf-8')
                    
                    # Check if the status object was created and if it has a non-zero error code
                    if pisa_status and not pisa_status.err: # type: ignore
                        result["success"] = True
                        result["pdf_path"] = pdf_filepath
                    else:
                        error_code = getattr(pisa_status, 'err', -1) # Safely get error code
                        error_msg = f"Error generating PDF. Error code: {error_code}"
                        logger.error(error_msg)
                        result["error"] = error_msg
                else:
                    error_msg = "xhtml2pdf is not available."
                    logger.error(error_msg)
                    result["error"] = error_msg
        except Exception as e:
            error_msg = f"Unexpected error during PDF generation: {e}"
            logger.error(error_msg, exc_info=True)
            result["error"] = error_msg
            # Try to save debug HTML even on unexpected errors
            html_debug_filepath = os.path.splitext(pdf_filepath)[0] + "_debug.html"
            try:
                with open(html_debug_filepath, "w", encoding="utf-8") as f_html:
                    f_html.write(full_html)
            except Exception as e_debug:
                logger.error(f"Failed to save debug HTML file: {e_debug}")
        finally:
            self._close_db_connection()
            
        return result

    def get_run_summary(self, run_id: int) -> Dict[str, Any]:
        """
        Compute summary metrics for a run and return them as structured data.

        This provides a programmatic overview without generating a PDF.
        
        Args:
            run_id: The ID of the run to analyze
            
        Returns:
            Dictionary containing:
            - success: bool indicating if operation was successful
            - run_info: dictionary with basic run information
            - metrics: dictionary with calculated metrics
            - error: optional error message
        """
        result = {
            "success": False,
            "run_info": {},
            "metrics": {},
            "error": None
        }
        
        run_data, steps = self._fetch_run_and_steps_data(run_id)

        if not run_data:
            error_msg = f"Run ID {run_id} not found. No summary available."
            result["error"] = error_msg
            self._close_db_connection()
            return result

        steps = steps or []
        metrics_data = self._calculate_summary_metrics(run_id, run_data, steps)
        
        # Structure the run information
        result["run_info"] = {
            "run_id": run_id,
            "app_package": run_data['app_package'],
            "start_activity": run_data['start_activity'],
            "start_time": run_data['start_time'] or 'N/A',
            "end_time": run_data['end_time'] or 'N/A'
        }
        
        # Include all metrics
        result["metrics"] = metrics_data
        result["success"] = True

        self._close_db_connection()
        return result
