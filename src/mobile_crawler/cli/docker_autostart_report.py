"""Console reporting for the CLI's Docker container auto-start attempts."""

import click


def report_docker_autostart(label: str, result: tuple[bool, str] | None) -> None:
    """Echo the outcome of a Docker container auto-start attempt (a no-op if `result` is None).

    Always writes to stderr, never stdout: stdout is reserved for the
    command's machine-readable output (e.g. crawl's newline-delimited JSON events).
    """
    if result is None:
        return
    ok, message = result
    if ok:
        click.echo(f"{label}: {message}", err=True)
    else:
        click.echo(f"Warning: {label} could not be started automatically: {message}", err=True)
