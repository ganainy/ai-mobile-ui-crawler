"""CLI commands for Mobilerun Portal, the on-device app that supplies the accessibility tree."""

import click

_device_option = click.option("--device", required=True, help="Device ID (see 'adb devices')")


def _report(text: str, ready: bool) -> None:
    """Print the status; when Portal is not ready, print the manual steps and exit 1."""
    from mobile_crawler.core.portal_actions import PORTAL_MANUAL_STEPS

    click.echo(text)
    if not ready:
        click.echo(PORTAL_MANUAL_STEPS, err=True)
        click.get_current_context().exit(1)


@click.group()
def portal():
    """Check, enable or install Mobilerun Portal on a device.

    The 'boost' and 'accessibility' UI parser modes need Portal installed with
    its accessibility service on. The crawler reads Portal over adb; the Portal
    app's Mobilerun sign-in, API key, IP and token are not needed.
    """


@portal.command()
@_device_option
def status(device: str):
    """Show whether Portal is installed and its accessibility service is on (changes nothing)."""
    from mobile_crawler.core.portal_actions import check_portal

    _report(*check_portal(device))


@portal.command()
@_device_option
def enable(device: str):
    """Turn on Portal's accessibility service over adb (installs Portal first if it is missing)."""
    from mobile_crawler.core.portal_actions import fix_portal

    _report(*fix_portal(device))


@portal.command()
@_device_option
def install(device: str):
    """Download the pinned Portal release, (re)install it and turn on its accessibility service."""
    from mobile_crawler.core.portal_actions import install_portal

    click.echo("Installing Portal (this can take a few minutes)...", err=True)
    _report(*install_portal(device))
