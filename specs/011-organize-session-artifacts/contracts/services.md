# Internal Contracts: Organize Session Artifacts

## SessionFolderManager

```python
class SessionFolderManager:
    def create_session_folder(self, run_id: int, device_id: str, app_package: str) -> str:
        """Creates the run_ID_TS folder and returns the absolute path."""
    
    def get_session_path(self, run: Run) -> Optional[str]:
        """Resolves path from DB or heuristics."""
        
    def get_subfolder(self, run_id: int, subfolder_name: str) -> str:
        """Returns the path to a specific subfolder (e.g. 'screenshots'), creating it if needed."""
```

## ScreenshotCapture

```python
class ScreenshotCapture:
    def __init__(self, driver: AppiumDriver, run_id: int, session_manager: SessionFolderManager):
        """Now requires session_manager to resolve save paths."""
```

## RunExporter

```python
class RunExporter:
    def export_run(self, run_id: int, output_dir: Optional[Path] = None) -> Path:
        """If output_dir is None, it should now default to {session_path}/data/."""
```

## MobSFManager

```python
class MobSFManager:
    def analyze_run(self, run_id: int, package: str, device_id: str) -> MobSFAnalysisResult:
        """Must use session_manager to find 'reports' subfolder."""
```
