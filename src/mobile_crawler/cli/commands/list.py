"""CLI commands for listing runs and devices."""

import click


@click.command()
@click.argument('target', type=click.Choice(['runs', 'devices']))
@click.option('--limit', '-n', type=int, default=10, help='Maximum number of items to list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list(target: str, limit: int, output_format: str):
    """List runs or devices.

    TARGET: What to list ('runs' or 'devices')
    """
    try:
        from mobile_crawler.infrastructure.database import DatabaseManager
        from mobile_crawler.infrastructure.run_repository import RunRepository
        from mobile_crawler.infrastructure.device_detection import DeviceDetector
        
        db_manager = DatabaseManager()
        
        if target == 'runs':
            run_repository = RunRepository(db_manager)
            runs = run_repository.get_recent_runs(limit)
            
            if output_format == 'json':
                import json
                runs_data = []
                for run in runs:
                    runs_data.append({
                        'id': run.id,
                        'device_id': run.device_id,
                        'app_package': run.app_package,
                        'start_time': run.start_time.isoformat() if run.start_time else None,
                        'status': run.status,
                        'total_steps': run.total_steps,
                        'unique_screens': run.unique_screens
                    })
                click.echo(json.dumps(runs_data, indent=2))
            else:
                if not runs:
                    click.echo("No runs found.")
                    return
                
                # Table format
                click.echo("Recent Runs:")
                click.echo("-" * 80)
                click.echo(f"{'ID':<5} {'Device':<15} {'App':<20} {'Status':<10} {'Steps':<6} {'Screens':<7} {'Start Time'}")
                click.echo("-" * 80)
                for run in runs:
                    start_time = run.start_time.strftime("%Y-%m-%d %H:%M") if run.start_time else "N/A"
                    click.echo(f"{run.id:<5} {run.device_id:<15} {run.app_package[:19]:<20} {run.status:<10} {run.total_steps:<6} {run.unique_screens:<7} {start_time}")
        
        elif target == 'devices':
            device_detector = DeviceDetector()
            devices = device_detector.get_connected_devices()
            
            if output_format == 'json':
                import json
                devices_data = []
                for device in devices[:limit]:
                    devices_data.append({
                        'id': device.id,
                        'name': device.name,
                        'platform': device.platform,
                        'version': device.version,
                        'status': device.status
                    })
                click.echo(json.dumps(devices_data, indent=2))
            else:
                if not devices:
                    click.echo("No devices found.")
                    return
                
                # Table format
                click.echo("Connected Devices:")
                click.echo("-" * 60)
                click.echo(f"{'ID':<20} {'Name':<20} {'Platform':<10} {'Version':<10} {'Status'}")
                click.echo("-" * 60)
                for device in devices[:limit]:
                    click.echo(f"{device.id:<20} {device.name[:19]:<20} {device.platform:<10} {device.version:<10} {device.status}")
                
    except Exception as e:
        click.echo(f"Error listing {target}: {e}", err=True)
        raise click.Abort()