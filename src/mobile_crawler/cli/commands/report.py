"""CLI commands for report generation."""

import click


@click.command()
@click.argument("run_id")
@click.option("--output", "-o", "output_path", type=click.Path(), help="Output path for the HTML report")
def report(run_id: str, output_path: str):
    """Generate a report for a crawl run.

    Writes the HTML report and the AI-readable analysis folder (analysis.md, steps.jsonl,
    run.json) into the run's session folder, and reads Phoenix/Langfuse telemetry back in.

    RUN_ID: ID of the crawl run to generate report for
    """
    try:
        from mobile_crawler.config.config_manager import ConfigManager
        from mobile_crawler.domain.report_generator import ReportGenerator
        from mobile_crawler.infrastructure.database import DatabaseManager
        from mobile_crawler.infrastructure.telemetry_client import build_telemetry_client_factory

        run_id_int = int(run_id)

        db_manager = DatabaseManager()
        db_manager.migrate_schema()
        report_generator = ReportGenerator(
            db_manager,
            telemetry_client_factory=build_telemetry_client_factory(ConfigManager()),
        )

        path = report_generator.generate(run_id_int, output_path, fetch_telemetry=True)
        click.echo(f"Run report generated: {path}")

    except ValueError as e:
        click.echo(f"Invalid run ID: {run_id}", err=True)
        raise click.Abort() from e
    except Exception as e:
        click.echo(f"Error generating report: {e}", err=True)
        raise click.Abort() from e
