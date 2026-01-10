"""Main CLI entry point using Click."""

import click
from pathlib import Path

# Import version from package
try:
    from importlib.metadata import version
    __version__ = version("mobile-crawler")
except ImportError:
    # Fallback for older Python versions
    __version__ = "0.1.0"


@click.group()
@click.version_option(__version__, prog_name="mobile-crawler")
def cli():
    """Mobile Crawler - AI-powered Android exploration tool.

    Automate mobile app testing and exploration using AI to discover
    app functionality and generate comprehensive reports.
    """
    pass


# Import and register commands
from mobile_crawler.cli.commands.crawl import crawl
from mobile_crawler.cli.commands.config import config
from mobile_crawler.cli.commands.report import report
from mobile_crawler.cli.commands.list import list
from mobile_crawler.cli.commands.delete import delete
cli.add_command(crawl)
cli.add_command(config)
cli.add_command(report)
cli.add_command(list)
cli.add_command(delete)


def run():
    """Run the CLI application."""
    cli()


if __name__ == "__main__":
    run()