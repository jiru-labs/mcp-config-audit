"""Tests for the CLI entrypoint."""

from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from mcp_scan import __version__, cli
from mcp_scan.cli import app
from mcp_scan.discovery import HOST_CLAUDE_DESKTOP, ConfigLocation

runner = CliRunner()


@pytest.fixture(autouse=True)
def wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    """Render tables wide enough that assertions see unwrapped cell text."""
    monkeypatch.setattr(cli, "console", Console(width=200, no_color=True))


def _pretend_claude_desktop_config_at(
    monkeypatch: pytest.MonkeyPatch, path: Path
) -> None:
    """Make discovery report Claude Desktop's config as living at `path`."""
    location = ConfigLocation(
        host=HOST_CLAUDE_DESKTOP, path=path, exists=path.is_file()
    )
    monkeypatch.setattr(cli, "find_claude_desktop_config", lambda: location)


def test_version_command_prints_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])

    assert result.exit_code != 0
    assert "version" in result.stdout


def test_list_shows_a_table_of_servers_from_a_config(sample_config: Path) -> None:
    result = runner.invoke(app, ["list", "--config", str(sample_config)])

    assert result.exit_code == 0
    assert "MCP servers" in result.stdout
    assert "filesystem" in result.stdout
    assert "github" in result.stdout
    assert "remote-notes" in result.stdout
    assert "https://notes.example.com/mcp" in result.stdout


def test_list_shows_env_var_keys_but_never_their_values(
    sample_config: Path, sample_secrets: list[str]
) -> None:
    result = runner.invoke(app, ["list", "--config", str(sample_config)])

    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in result.stdout
    assert "NOTES_API_KEY" in result.stdout
    assert sample_secrets  # the fixture must actually carry secrets to test
    for secret in sample_secrets:
        assert secret not in result.stdout


def test_list_warns_on_malformed_config_without_crashing(
    malformed_config: Path,
) -> None:
    result = runner.invoke(app, ["list", "--config", str(malformed_config)])

    assert result.exit_code == 0
    assert result.exception is None
    assert "malformed JSON" in result.stdout


def test_list_discovers_installed_hosts_when_no_config_given(
    monkeypatch: pytest.MonkeyPatch, sample_config: Path
) -> None:
    _pretend_claude_desktop_config_at(monkeypatch, sample_config)

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "filesystem" in result.stdout


def test_list_reports_when_no_config_is_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _pretend_claude_desktop_config_at(monkeypatch, tmp_path / "missing.json")

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No MCP config files found." in result.stdout


def test_list_reports_a_config_that_declares_no_servers(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")

    result = runner.invoke(app, ["list", "--config", str(empty)])

    assert result.exit_code == 0
    assert "No MCP servers" in result.stdout
