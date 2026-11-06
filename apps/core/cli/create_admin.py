"""Command to create a local JWT-mode admin user."""

import asyncio

import typer
from pydantic import ValidationError as PydanticValidationError

from apps.core.db import DatabaseManager
from apps.core.exceptions import BaseAPIException
from config.settings import settings


def create_admin(
    username: str = typer.Option(..., "--username", "-u", prompt=True),
    email: str = typer.Option(..., "--email", "-e", prompt=True),
    password: str = typer.Option(
        ...,
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Prompted (hidden) if omitted; avoid passing it on the command line.",
    ),
) -> None:
    """Create a local user with the admin role (JWT auth mode).

    If the username already exists, the admin role is granted to that user and
    the password is left unchanged. Requires applied migrations.
    """
    from apps.auth.jwt import schemas
    from apps.auth.jwt.services import rbac_service

    if not settings.database.ENABLED:
        typer.echo("[ERROR] Database is not enabled in settings", err=True)
        raise typer.Exit(1)

    try:
        data = schemas.RegisterRequest(
            username=username, email=email, password=password
        )
    except PydanticValidationError as e:
        for error in e.errors():
            field = ".".join(str(part) for part in error["loc"])
            typer.echo(f"[ERROR] {field}: {error['msg']}", err=True)
        raise typer.Exit(1) from e

    async def run() -> None:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        try:
            async with db_manager.get_session_maker()() as db:
                access = await rbac_service.create_admin(db, data)
        finally:
            await db_manager.close()
        typer.echo(
            f"[OK] {data.username} ({access.user_id}) has roles: "
            f"{', '.join(access.effective_roles)}"
        )

    try:
        asyncio.run(run())
    except BaseAPIException as e:
        typer.echo(f"[ERROR] {e.message}", err=True)
        raise typer.Exit(1) from e
