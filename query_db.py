import sqlite3
from mobile_crawler.config import get_app_data_dir

db_path = get_app_data_dir() / "mobile_crawler.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

run = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
if not run:
    print("No runs found")
    exit(0)
    
print(f"Run ID: {run['id']}, Status: {run['status']}, Error: {run['error']}")

steps = conn.execute("SELECT step_number, action_type, error_message FROM step_logs WHERE run_id = ? ORDER BY step_number", (run['id'],)).fetchall()
for step in steps:
    print(f"Step {step['step_number']} ({step['action_type']}): Error: {step['error_message']}")
