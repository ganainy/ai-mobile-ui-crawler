"""CLI command for deleting runs."""

import click
import shutil
from pathlib import Path


@click.command()
@click.argument('run_id')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
def delete(run_id: str, yes: bool):
    """Delete a crawl run and all associated data.

    RUN_ID: ID of the crawl run to delete
    """
    try:
        from mobile_crawler.infrastructure.database import DatabaseManager
        from mobile_crawler.infrastructure.run_repository import RunRepository
        from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager
        
        # Parse run ID
        try:
            run_id_int = int(run_id)
        except ValueError:
            click.echo(f"Invalid run ID: {run_id}", err=True)
            raise click.Abort()
        
        # Initialize database and repository
        db_manager = DatabaseManager()
        run_repository = RunRepository(db_manager)
        session_folder_manager = SessionFolderManager()
        
        # Get run details first
        run = run_repository.get_run_by_id(run_id_int)
        if run is None:
            click.echo(f"Run not found: {run_id}", err=True)
            raise click.Abort()
        
        # Show run details
        click.echo(f"Run ID: {run.id}")
        click.echo(f"Device: {run.device_id}")
        click.echo(f"App: {run.app_package}")
        click.echo(f"Status: {run.status}")
        click.echo(f"Steps: {run.total_steps}")
        click.echo(f"Screens: {run.unique_screens}")
        
        # Confirm deletion
        if not yes:
            confirm = click.confirm(
                "This will permanently delete this run and all associated data. Continue?",
                default=False
            )
            if not confirm:
                click.echo("Deletion cancelled.")
                return
        
        # Delete session folder if it exists
        session_folder = session_folder_manager.get_session_folder(run.device_id, run.app_package, run.start_time)
        if session_folder.exists():
            try:
                shutil.rmtree(session_folder)
                click.echo(f"Deleted session folder: {session_folder}")
            except Exception as e:
                click.echo(f"Warning: Could not delete session folder: {e}", err=True)
        
        # Delete run from database (cascading delete will handle related records)
        deleted = run_repository.delete_run(run_id_int)
        if deleted:
            click.echo(f"Deleted run {run_id} from database.")
        else:
            click.echo(f"Failed to delete run {run_id} from database.", err=True)
            raise click.Abort()
        
        click.echo(f"Run {run_id} deleted successfully.")
        
    except ValueError as e:
        click.echo(f"Invalid run ID: {run_id}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error deleting run: {e}", err=True)
        raise click.Abort()
