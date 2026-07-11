"""Shared fixtures for the test suite."""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_config() -> Path:
    """A well-formed config with a local, a credentialed and a remote server."""
    return FIXTURES_DIR / "sample_config.json"


@pytest.fixture
def malformed_config() -> Path:
    """A config whose JSON does not parse."""
    return FIXTURES_DIR / "malformed_config.json"


@pytest.fixture
def sample_secrets(sample_config: Path) -> list[str]:
    """Every env var value in the sample config.

    Read straight from the fixture so the guarantee still holds if the fixture
    changes: none of these strings may ever reach a parse result or the
    terminal.
    """
    data = json.loads(sample_config.read_text(encoding="utf-8"))
    return [
        value
        for server in data["mcpServers"].values()
        for value in server.get("env", {}).values()
    ]
