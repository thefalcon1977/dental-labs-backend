"""Command to show configuration settings."""

import traceback

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config.settings import settings

from .utils import format_config_value, get_all_settings, organize_config

console = Console()


def show_config() -> None:
    """Show all applied configurations automatically discovered from settings.

    Displays configuration in a Typer-style formatted table with sections
    and organized settings. Filters out Dynaconf internals and shows only
    user-relevant configuration.
    """
    try:
        config_dict = get_all_settings()

        if not config_dict:
            typer.echo("\n[WARN] No configuration found")
            return

        organized = organize_config(config_dict)

        # Create main table for configuration
        main_table = Table(
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
            box=None,  # Use simple borders like Typer
            padding=(0, 1),
        )
        main_table.add_column("Setting", style="cyan", no_wrap=False, width=35)
        main_table.add_column("Value", style="yellow", overflow="fold", width=50)

        # Add environment info at the top
        env = settings.current_env or "default"
        main_table.add_row(
            "[bold]Environment[/bold]",
            f"[bold]{env}[/bold]",
            style="dim",
        )

        # Add configuration sections
        for section in sorted(organized.keys()):
            section_config = organized[section]
            if not section_config:
                continue

            section_name = section.replace("_", " ").title()

            # Add section header (Typer style - no emojis, just bold text)
            main_table.add_row(
                f"[bold cyan]{section_name}[/bold cyan]",
                "",
                style="dim",
            )

            # Add settings in this section
            for key, value in sorted(section_config.items()):
                formatted_value = format_config_value(value, key)
                display_key = key.replace("_", " ").title()
                main_table.add_row(f"  {display_key}", formatted_value)

        # Display the table in a panel
        console.print()
        console.print(
            Panel(
                main_table,
                title="[bold green]Configuration Settings[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )
        console.print()

    except Exception as e:
        typer.echo(f"\n[ERROR] Error loading configuration: {e}", err=True)
        if settings.DEBUG:
            typer.echo(traceback.format_exc(), err=True)
