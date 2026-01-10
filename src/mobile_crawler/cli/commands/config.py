"""CLI commands for configuration management."""

import json
from typing import Any, Optional

import click

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.config import get_app_data_dir


@click.group()
def config():
    """Manage configuration settings and API keys."""
    pass


@config.command()
@click.argument('key')
@click.argument('value')
def set(key: str, value: str):
    """Set a configuration value.

    KEY: Configuration key to set
    VALUE: Value to set (will be parsed as appropriate type)
    """
    try:
        # Ensure app data directory exists
        app_data_dir = get_app_data_dir()
        app_data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize config manager
        config_manager = ConfigManager()
        config_manager.user_config_store.create_schema()

        # Try to parse the value as JSON first, then as other types
        parsed_value: Any = value
        try:
            parsed_value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            # Try to convert to int/float/bool
            if value.lower() in ('true', 'false'):
                parsed_value = value.lower() == 'true'
            elif value.isdigit():
                parsed_value = int(value)
            elif '.' in value and value.replace('.', '').isdigit():
                parsed_value = float(value)
            # Otherwise keep as string

        # Check if this is a secret (API key)
        secret_keys = ['api_key', 'apikey', 'key', 'token', 'secret', 'password']
        is_secret = any(secret_key in key.lower() for secret_key in secret_keys)

        if is_secret:
            # Store as encrypted secret
            config_manager.user_config_store.set_secret_plaintext(key, str(parsed_value))
            click.echo(f"Set encrypted secret: {key}")
        else:
            # Store as regular setting
            config_manager.set(key, parsed_value)
            click.echo(f"Set config: {key} = {parsed_value}")

    except Exception as e:
        click.echo(f"Error setting config: {e}", err=True)
        raise click.Abort()


@config.command()
@click.argument('key')
def get(key: str):
    """Get a configuration value.

    KEY: Configuration key to retrieve
    """
    try:
        # Initialize config manager
        config_manager = ConfigManager()
        config_manager.user_config_store.create_schema()

        # Try to get as regular setting first
        value = config_manager.get(key)
        if value is not None:
            if isinstance(value, (dict, list)):
                click.echo(json.dumps(value, indent=2))
            else:
                click.echo(value)
            return

        # Try to get as secret
        try:
            secret_value = config_manager.user_config_store.get_secret_plaintext(key)
            if secret_value is not None:
                click.echo(f"[ENCRYPTED] {secret_value}")
                return
        except Exception:
            pass

        click.echo(f"Config key not found: {key}", err=True)
        raise click.Abort()

    except Exception as e:
        click.echo(f"Error getting config: {e}", err=True)
        raise click.Abort()


@config.command()
def list():
    """List all configuration settings."""
    try:
        # Initialize config manager
        config_manager = ConfigManager()
        config_manager.user_config_store.create_schema()

        # Get all settings
        settings = config_manager.user_config_store.get_all_settings()

        if not settings:
            click.echo("No configuration settings found.")
            return

        # Display settings
        click.echo("Configuration Settings:")
        click.echo("-" * 40)
        for key, value in sorted(settings.items()):
            if isinstance(value, (dict, list)):
                click.echo(f"{key}: {json.dumps(value)}")
            else:
                click.echo(f"{key}: {value}")

        # Check for secrets (we can't list them without decryption)
        conn = config_manager.user_config_store.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key FROM secrets")
        secret_keys = [row['key'] for row in cursor.fetchall()]

        if secret_keys:
            click.echo()
            click.echo("Encrypted Secrets:")
            click.echo("-" * 40)
            for key in sorted(secret_keys):
                click.echo(f"{key}: [ENCRYPTED]")

    except Exception as e:
        click.echo(f"Error listing config: {e}", err=True)
        raise click.Abort()