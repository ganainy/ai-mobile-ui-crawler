"""Main CLI entry point using Click."""


import click

from mobile_crawler.cli.commands.config import config
from mobile_crawler.cli.commands.crawl import crawl
from mobile_crawler.cli.commands.delete import delete
from mobile_crawler.cli.commands.list import list
from mobile_crawler.cli.commands.mobsf_scan import mobsf_scan
from mobile_crawler.cli.commands.portal import portal
from mobile_crawler.cli.commands.report import report
from mobile_crawler.cli.commands.scenarios import scenarios
from mobile_crawler.cli.commands.stats import stats

try:
    from importlib.metadata import version
    __version__ = version("mobile-crawler")
except ImportError:
    # Fallback for older Python versions
    __version__ = "0.1.0"


@click.group(epilog="Run 'mobile-crawler-cli COMMAND --help' for a command's options. Full reference: docs/cli.md")
@click.version_option(__version__, prog_name="mobile-crawler")
def cli():
    """Mobile Crawler - AI-powered Android exploration tool.

    Automate mobile app testing and exploration using AI to discover
    app functionality and generate comprehensive reports.
    """
    pass


cli.add_command(crawl)
cli.add_command(config)
cli.add_command(report)
cli.add_command(list)
cli.add_command(delete)
cli.add_command(mobsf_scan)
cli.add_command(scenarios)
cli.add_command(stats)
cli.add_command(portal)


def run():
    """Run the CLI application."""
    cli()


if __name__ == "__main__":
    run()
