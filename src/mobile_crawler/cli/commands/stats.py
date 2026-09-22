"""CLI command for showing a run's persisted statistics."""

import click


@click.command()
@click.argument("run_id")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
def stats(run_id: str, output_format: str):
    """Show the persisted statistics of a crawl run.

    The same run_stats record as the GUI's Run History "View Stats" dialog.
    Stats are saved when a crawl completes.

    RUN_ID: ID of the crawl run
    """
    try:
        run_id_int = int(run_id)
    except ValueError as e:
        click.echo(f"Invalid run ID: {run_id}", err=True)
        raise click.Abort() from e

    try:
        from mobile_crawler.core.run_stats_sections import (
            RUN_STATS_SECTIONS,
            format_stat_value,
            persisted_stats_dict,
        )
        from mobile_crawler.infrastructure.database import DatabaseManager
        from mobile_crawler.infrastructure.run_repository import RunRepository
        from mobile_crawler.infrastructure.run_stats_repository import RunStatsRepository
        from mobile_crawler.infrastructure.step_phase_repository import StepPhaseRepository

        db_manager = DatabaseManager()
        db_manager.migrate_schema()

        run = RunRepository(db_manager).get_run_by_id(run_id_int)
        if run is None:
            click.echo(f"Run {run_id_int} not found.", err=True)
            raise click.Abort()

        run_stats = RunStatsRepository(db_manager).get_run_stats(run_id_int)
        if run_stats is None:
            click.echo(
                f"No persisted statistics for run {run_id_int}. Stats are saved when a crawl "
                "completes; runs that crashed or predate run_stats have none.",
                err=True,
            )
            raise click.Abort()

        # Phase transitions live in their own table, not in run_stats.
        phases = StepPhaseRepository(db_manager).get_run_phase_stats(run_id_int)

        if output_format == "json":
            import json

            data = {
                "run_id": run_id_int,
                "app_package": run.app_package,
                "status": run.status,
                **persisted_stats_dict(run_stats),
                "phases": phases,
            }
            click.echo(json.dumps(data, indent=2))
            return

        click.echo(f"Run {run_id_int} Statistics ({run.app_package}, {run.status})")
        sections = [
            (title, [(label, getattr(run_stats, attr, None)) for label, attr in rows])
            for title, rows in RUN_STATS_SECTIONS
        ]
        sections.append(
            (
                "Phases",
                [
                    ("Phase Transitions", phases["total_transitions"]),
                    ("Full Cycles", phases["phases_completed"]),
                    ("Avg Step Span (ms)", phases["avg_step_duration_ms"]),
                ],
            )
        )
        label_width = max(len(label) for _, rows in sections for label, _ in rows)
        for title, rows in sections:
            click.echo("")
            click.echo(title)
            click.echo("-" * len(title))
            for label, value in rows:
                # ASCII placeholder: an em dash garbles on non-UTF-8 Windows pipes.
                click.echo(f"  {label:<{label_width}}  {format_stat_value(value, missing='-')}")

    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"Error reading stats: {e}", err=True)
        raise click.Abort() from e
