"""Pick the device a CLI command talks to: the one given with --device, else the only connected one."""

import click

from mobile_crawler.infrastructure.device_detection import DeviceDetection, DeviceDetectionError

DEVICE_HELP = "Device ID (see 'list devices'); only needed when more than one device is connected"


def resolve_device(device_id: str | None) -> str:
    """Return `device_id`, or the ID of the single available device when it is None.

    Raises click.UsageError when no device, or more than one, is available.
    """
    if device_id:
        return device_id
    try:
        devices = DeviceDetection().get_available_devices()
    except DeviceDetectionError as e:
        raise click.ClickException(f"Could not list devices: {e}") from e
    if not devices:
        raise click.UsageError("No device connected (status 'device'); connect one or pass --device ID.")
    if len(devices) > 1:
        ids = ", ".join(d.device_id for d in devices)
        raise click.UsageError(f"{len(devices)} devices connected ({ids}); pick one with --device ID.")
    # stderr: some commands (crawl) stream JSON on stdout.
    click.echo(f"Using device {devices[0].device_id} (the only one connected).", err=True)
    return devices[0].device_id
