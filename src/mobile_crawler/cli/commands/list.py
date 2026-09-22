"""CLI commands for listing runs, devices and installed apps."""

from __future__ import annotations

import logging

import click

logger = logging.getLogger(__name__)


@click.command()
@click.argument('target', type=click.Choice(['runs', 'devices', 'apps']))
@click.option('--limit', '-n', type=int, default=None,
              help='Maximum number of items to list (default: 10 for runs/devices, all for apps)')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.option('--device', '-d', 'device_id', default=None, help='Device ID to list apps from (required for apps)')
@click.option('--no-names', is_flag=True, default=False,
              help='apps only: skip resolving app names (faster; names need an APK pull on first lookup)')
def list(target: str, limit: int | None, output_format: str, device_id: str | None, no_names: bool):
    """List runs, devices or installed apps.

    TARGET: What to list ('runs', 'devices' or 'apps')

    'apps' lists the third-party packages installed on --device, i.e. valid
    values for `crawl --package`.
    """
    if target == 'apps' and not device_id:
        raise click.UsageError("'list apps' requires --device ID (see 'list devices').")
    if target != 'apps' and (device_id or no_names):
        raise click.UsageError("--device and --no-names only apply to 'list apps'.")
    if limit is None and target != 'apps':
        limit = 10

    try:
        from mobile_crawler.infrastructure.database import DatabaseManager
        from mobile_crawler.infrastructure.device_detection import DeviceDetection
        from mobile_crawler.infrastructure.run_repository import RunRepository

        if target == 'runs':
            db_manager = DatabaseManager()
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
            device_detection = DeviceDetection()
            devices = device_detection.get_connected_devices()

            if output_format == 'json':
                import json
                devices_data = []
                for device in devices[:limit]:
                    devices_data.append({
                        'id': device.device_id,
                        'name': device.model,
                        'platform': 'Android',
                        'version': device.android_version,
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
                    click.echo(f"{device.device_id:<20} {device.model[:19]:<20} {'Android':<10} {device.android_version:<10} {device.status}")

        elif target == 'apps':
            _list_apps(device_id, limit, output_format, resolve_names=not no_names)

    except Exception as e:
        click.echo(f"Error listing {target}: {e}", err=True)
        raise click.Abort() from e


def _list_apps(device_id: str, limit: int | None, output_format: str, resolve_names: bool) -> None:
    """Print the third-party packages installed on `device_id`, with app names where resolvable."""
    from mobile_crawler.infrastructure import installed_apps

    packages = installed_apps.list_third_party_packages(device_id)
    if limit is not None:
        packages = packages[:limit]

    names = _resolve_app_names(device_id, packages) if resolve_names else {}
    apps = [{'package': package, 'name': names.get(package)} for package in packages]

    if output_format == 'json':
        import json
        click.echo(json.dumps(apps, indent=2))
        return

    if not apps:
        click.echo(f"No third-party apps found on {device_id}.")
        return

    click.echo(f"Installed Apps on {device_id}:")
    click.echo("-" * 80)
    click.echo(f"{'Package':<50} {'Name'}")
    click.echo("-" * 80)
    for app in apps:
        click.echo(f"{app['package']:<50} {app['name'] or '-'}")


def _resolve_app_names(device_id: str, packages: list[str]) -> dict[str, str]:
    """Resolve display names via the GUI's AppMetadataResolver; unresolved packages are omitted."""
    from mobile_crawler.infrastructure.app_metadata_resolver import AppMetadataResolver

    if packages:
        # stderr: stdout may be JSON. First lookups pull each APK, so this can take a while.
        click.echo(f"Resolving names for {len(packages)} apps (use --no-names to skip)...", err=True)
    resolver = AppMetadataResolver()
    names = {}
    for package in packages:
        try:
            metadata = resolver.resolve(device_id, package)
        except Exception as e:
            logger.debug(f"Failed to resolve app metadata for {package}: {e}")
            continue
        if metadata.source != 'unresolved':
            names[package] = metadata.label
    return names
