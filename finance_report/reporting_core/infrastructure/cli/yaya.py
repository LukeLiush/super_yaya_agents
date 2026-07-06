import asyncio

import typer
from rich.console import Console

from finance_report.finance_sdk.http_client import HttpFinanceReportClient
from finance_report.finance_sdk.schemas import ReportTriggerRequest, ReportType

app = typer.Typer(name="yaya", help="Yaya CLI for investment analysis")
finance_app = typer.Typer(help="Finance related commands")
app.add_typer(finance_app, name="finance")

console = Console()


def get_client():
    return HttpFinanceReportClient()


def _get_selected_report_types(ctx: typer.Context) -> list[ReportType]:
    selected_types: list[ReportType] = []
    # 1. Get all valid enum strings: ['--price', '--insider']
    valid_flags = {f"--{rt.value}": rt for rt in ReportType}

    args = ctx.args or []
    for arg in args:
        if arg in valid_flags:
            selected_types.append(valid_flags[arg])
        else:
            # Raise error for truly unknown options
            raise typer.BadOption(f"Unknown option: {arg}")

    # Default fallback
    if not selected_types:
        return [rt for rt in ReportType]
    return selected_types


@finance_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    help=f"Trigger a new report. Available flags: {', '.join(['--' + rt.value for rt in ReportType])}",
)
def trigger(
    ctx: typer.Context,
    ticker: str = typer.Argument(..., help="The stock ticker symbol"),
):
    selected_types = _get_selected_report_types(ctx)

    client = get_client()

    async def run_trigger():
        report_trigger_request = ReportTriggerRequest(ticker=ticker, report_types=selected_types)
        console.print(f"Triggering report for {report_trigger_request}...")
        try:
            resp = await client.trigger_report_generation(report_trigger_request=report_trigger_request)
            console.print(f"[green]Successfully triggered report for {ticker}[/green]")
            console.print(f"Message: {resp.message}")
            console.print(f"Report ID: [bold]{resp.id}[/bold]")
        except Exception as e:
            console.print(f"[red]Error triggering report: {e}[/red]")

    asyncio.run(run_trigger())


@finance_app.command()
def show(
    report_id: str = typer.Argument(..., help="The report ID to show"),
):
    """Show report results for a given report ID."""
    # Since we don't have a specific 'show' endpoint in the current SDK that matches this exact need
    # (the SDK seems to only have trigger_report), we might need to implement it or use a placeholder.
    # Looking at the previous design, 'show' was mentioned.
    console.print(f"Fetching results for report ID: {report_id}...")
    console.print(
        "[yellow]Show command is partially implemented. "
        "In a real scenario, this would fetch data from the API.[/yellow]"
    )


@finance_app.command()
def status(
    report_id: str = typer.Argument(..., help="The report ID to check status for"),
):
    """Check the status of a report generation."""
    console.print(f"Checking status for report ID: {report_id}...")
    console.print("[yellow]Status command is partially implemented.[/yellow]")


if __name__ == "__main__":
    app()
