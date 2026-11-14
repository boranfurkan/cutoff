"""Export CLI for the finance team."""
from datetime import datetime

import typer

app = typer.Typer(add_completion=False)


@app.command()
def export(since: datetime, fmt: str = "csv"):
    """Export transactions since a date.

    SINCE must be a calendar date or date-time such as 2025-03-01. Anything else, including bare numbers,
    is rejected with a usage error: a mistyped invoice number once exported eight years of data.
    """
    typer.echo(f"exporting {fmt} since {since.date().isoformat()}")


@app.command()
def formats():
    typer.echo("csv json")
