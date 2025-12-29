"""
Persistent credential store for per-app authentication management.

Stores test credentials per app package name to enable:
- Login flow when credentials exist for an app
- Signup flow when no credentials exist, then store them for future use
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class CredentialStore:
    """
    SQLite-backed persistent store for per-app test credentials.
    
    Stores credentials by app package name so the AI can:
    - Use stored credentials for login if they exist
    - Create new account via signup if no credentials, then save them
    """
    
    TABLE_NAME = "app_credentials"
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the credential store.
        
        Args:
            db_path: Path to SQLite database. If None, uses default in output_data.
        """
        if db_path is None:
            # Default location in project output_data directory
            from utils.paths import find_project_root
            project_root = find_project_root(Path(__file__).parent)
            db_dir = project_root / "output_data" / "credentials"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "app_credentials.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                        package_name TEXT PRIMARY KEY,
                        email TEXT NOT NULL,
                        password TEXT NOT NULL,
                        name TEXT,
                        extra_data TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        signup_completed INTEGER DEFAULT 0,
                        login_count INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
                logger.info(f"Credential store initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize credential store: {e}")
            raise
    
    def get_credentials(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Get stored credentials for an app.
        
        Args:
            package_name: App package name (e.g., 'com.example.app')
            
        Returns:
            Dict with 'email', 'password', 'name', 'extra_data' or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT email, password, name, extra_data, signup_completed, login_count
                    FROM {self.TABLE_NAME}
                    WHERE package_name = ?
                """, (package_name,))
                row = cursor.fetchone()
                
                if row:
                    extra_data = {}
                    if row[3]:
                        try:
                            extra_data = json.loads(row[3])
                        except json.JSONDecodeError:
                            pass
                    
                    return {
                        "email": row[0],
                        "password": row[1],
                        "name": row[2],
                        "extra_data": extra_data,
                        "signup_completed": bool(row[4]),
                        "login_count": row[5] or 0
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get credentials for {package_name}: {e}")
            return None
    
    def has_credentials(self, package_name: str) -> bool:
        """Check if credentials exist for an app."""
        return self.get_credentials(package_name) is not None
    
    def store_credentials(
        self, 
        package_name: str, 
        email: str, 
        password: str,
        name: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        signup_completed: bool = True
    ) -> bool:
        """
        Store or update credentials for an app.
        
        Args:
            package_name: App package name
            email: Email/username for the account
            password: Password for the account
            name: Optional user name
            extra_data: Optional additional data (stored as JSON)
            signup_completed: Whether signup was successfully completed
            
        Returns:
            True if stored successfully
        """
        try:
            now = datetime.now().isoformat()
            extra_json = json.dumps(extra_data) if extra_data else None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    INSERT INTO {self.TABLE_NAME} 
                    (package_name, email, password, name, extra_data, created_at, updated_at, signup_completed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(package_name) DO UPDATE SET
                        email = excluded.email,
                        password = excluded.password,
                        name = excluded.name,
                        extra_data = excluded.extra_data,
                        updated_at = excluded.updated_at,
                        signup_completed = excluded.signup_completed
                """, (package_name, email, password, name, extra_json, now, now, int(signup_completed)))
                conn.commit()
                logger.info(f"Stored credentials for {package_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to store credentials for {package_name}: {e}")
            return False
    
    def increment_login_count(self, package_name: str) -> bool:
        """Increment the login count for an app (for metrics)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    UPDATE {self.TABLE_NAME}
                    SET login_count = login_count + 1, updated_at = ?
                    WHERE package_name = ?
                """, (datetime.now().isoformat(), package_name))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to increment login count for {package_name}: {e}")
            return False
    
    def delete_credentials(self, package_name: str) -> bool:
        """Delete credentials for an app."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    DELETE FROM {self.TABLE_NAME}
                    WHERE package_name = ?
                """, (package_name,))
                conn.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Deleted credentials for {package_name}")
                return deleted
        except Exception as e:
            logger.error(f"Failed to delete credentials for {package_name}: {e}")
            return False
    
    def list_all(self) -> list[Dict[str, Any]]:
        """List all stored credentials (passwords masked)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT package_name, email, name, signup_completed, login_count, created_at
                    FROM {self.TABLE_NAME}
                    ORDER BY updated_at DESC
                """)
                rows = cursor.fetchall()
                return [
                    {
                        "package_name": row[0],
                        "email": row[1],
                        "name": row[2],
                        "signup_completed": bool(row[3]),
                        "login_count": row[4] or 0,
                        "created_at": row[5]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to list credentials: {e}")
            return []


# Singleton instance for easy access
_credential_store: Optional[CredentialStore] = None


def get_credential_store() -> CredentialStore:
    """Get the global credential store instance."""
    global _credential_store
    if _credential_store is None:
        _credential_store = CredentialStore()
    return _credential_store
