"""CLI commands for report generation."""

import click


@click.command()
@click.argument('run_id')
@click.option('--output', '-o', 'output_path', type=click.Path(), help='Output path for the PDF report')
@click.option('--format', 'output_format', type=click.Choice(['pdf', 'html']), default='pdf', help='Output format')
def report(run_id: str, output_path: str, output_format: str):
    """Generate a report for a crawl run.

    RUN_ID: ID of the crawl run to generate report for
    """
    try:
        from mobile_crawler.infrastructure.database import DatabaseManager
        from mobile_crawler.domain.report_generator import ReportGenerator
        
        db_manager = DatabaseManager()
        report_generator = ReportGenerator(db_manager)
        
        run_id_int = int(run_id)
        
        if output_format == 'pdf':
            path = report_generator.generate(run_id_int, output_path)
            click.echo(f"PDF report generated: {path}")
        else:
            # For now, only PDF is supported
            click.echo("HTML format not yet implemented, generating PDF instead", err=True)
            path = report_generator.generate(run_id_int, output_path)
            click.echo(f"PDF report generated: {path}")
                
    except ValueError as e:
        click.echo(f"Invalid run ID: {run_id}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error generating report: {e}", err=True)
        raise click.Abort()