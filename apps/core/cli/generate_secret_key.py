"""Command to generate secret keys."""

import secrets

import typer


def generate_secret_key(
    length: int = typer.Option(
        64, "--length", "-l", help="Length of the secret key (minimum 32)"
    ),
) -> None:
    """Generate a secure random secret key for APP_SECRET_KEY configuration.

    The generated key is cryptographically secure and suitable for use as
    APP_SECRET_KEY in your .env file or environment variables.

    Minimum recommended length is 32 characters. Default is 64 characters.
    """
    if length < 32:
        typer.echo("[ERROR] Secret key length must be at least 32 characters", err=True)
        raise typer.Exit(1)

    secret_key = secrets.token_urlsafe(length)

    typer.echo("\n" + "=" * 60)
    typer.echo("Generated Secret Key")
    typer.echo("=" * 60)
    typer.echo(f"\nLength: {len(secret_key)} characters")
    typer.echo("\nSecret Key:")
    typer.echo(secret_key)
    typer.echo("\n" + "=" * 60)
    typer.echo("\nTo use this key, add it to your .env file:")
    typer.echo(f"APP_SECRET_KEY={secret_key}")
    typer.echo("\nOr set it as an environment variable:")
    typer.echo(f"export APP_SECRET_KEY={secret_key}")
    typer.echo("\n" + "=" * 60 + "\n")
