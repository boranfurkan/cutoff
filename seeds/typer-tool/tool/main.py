"""Deployment helper CLI."""
import click
import typer

app = typer.Typer(add_completion=False)


class Percent(click.ParamType):
    name = "percent"

    def convert(self, value, param, ctx):
        text = str(value)
        return float(text[:-1]) / 100 if text.endswith("%") else float(text)


@app.command()
def deploy(service: str, traffic: float = typer.Option(1.0, click_type=Percent()), dry_run: bool = False):
    typer.echo(f"{'would deploy' if dry_run else 'deploying'} {service} at {traffic:.2f}")


@app.command()
def version():
    typer.echo("1.0")


def as_click():
    """Expose the app as a Click command so it can be mounted in a Click group."""
    return typer.main.get_command(app)


def subcommands():
    return sorted(as_click().commands)
