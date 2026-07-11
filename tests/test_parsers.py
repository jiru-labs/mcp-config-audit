"""Tests for config parsing."""

import json
from pathlib import Path

from mcp_scan.parsers import (
    TRANSPORT_REMOTE,
    TRANSPORT_STDIO,
    TRANSPORT_UNKNOWN,
    parse_config_file,
)


def _write_config(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_parses_every_server_in_the_sample_config(sample_config: Path) -> None:
    result = parse_config_file(sample_config)

    assert result.warnings == []
    assert [server.name for server in result.servers] == [
        "filesystem",
        "github",
        "remote-notes",
    ]


def test_parses_a_local_server(sample_config: Path) -> None:
    result = parse_config_file(sample_config)
    server = next(s for s in result.servers if s.name == "filesystem")

    assert server.transport == TRANSPORT_STDIO
    assert server.command == "npx"
    assert server.args == (
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/demo",
    )
    assert server.url is None
    assert server.env_keys == ()
    assert server.source == sample_config
    assert server.endpoint == (
        "npx -y @modelcontextprotocol/server-filesystem /Users/demo"
    )


def test_parses_a_remote_server(sample_config: Path) -> None:
    result = parse_config_file(sample_config)
    server = next(s for s in result.servers if s.name == "remote-notes")

    assert server.transport == TRANSPORT_REMOTE
    assert server.command is None
    assert server.url == "https://notes.example.com/mcp"
    assert server.endpoint == "https://notes.example.com/mcp"


def test_records_env_var_keys_without_their_values(
    sample_config: Path, sample_secrets: list[str]
) -> None:
    result = parse_config_file(sample_config)
    server = next(s for s in result.servers if s.name == "github")

    assert server.env_keys == ("GITHUB_PERSONAL_ACCESS_TOKEN",)

    parsed = repr(result)
    assert sample_secrets  # the fixture must actually carry secrets to test
    for secret in sample_secrets:
        assert secret not in parsed


def test_malformed_json_warns_instead_of_raising(malformed_config: Path) -> None:
    result = parse_config_file(malformed_config)

    assert result.servers == []
    assert len(result.warnings) == 1
    assert "malformed JSON" in result.warnings[0]


def test_missing_file_warns_instead_of_raising(tmp_path: Path) -> None:
    result = parse_config_file(tmp_path / "nope.json")

    assert result.servers == []
    assert "not found" in result.warnings[0]


def test_unreadable_file_warns_instead_of_raising(tmp_path: Path) -> None:
    path = _write_config(tmp_path / "locked.json", {})
    path.chmod(0o000)

    try:
        result = parse_config_file(path)
        assert result.servers == []
        assert "could not read config" in result.warnings[0]
    finally:
        path.chmod(0o644)


def test_config_without_servers_key_is_not_a_warning(tmp_path: Path) -> None:
    path = _write_config(tmp_path / "empty.json", {"theme": "dark"})

    result = parse_config_file(path)

    assert result.servers == []
    assert result.warnings == []


def test_top_level_json_array_warns(tmp_path: Path) -> None:
    path = _write_config(tmp_path / "array.json", ["nope"])

    result = parse_config_file(path)

    assert result.servers == []
    assert "top level" in result.warnings[0]


def test_servers_key_of_the_wrong_type_warns(tmp_path: Path) -> None:
    path = _write_config(tmp_path / "bad.json", {"mcpServers": []})

    result = parse_config_file(path)

    assert result.servers == []
    assert "not a JSON object" in result.warnings[0]


def test_a_broken_server_entry_does_not_discard_its_siblings(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path / "mixed.json",
        {"mcpServers": {"broken": "npx server", "ok": {"command": "npx"}}},
    )

    result = parse_config_file(path)

    assert [server.name for server in result.servers] == ["ok"]
    assert "server 'broken' is not a JSON object" in result.warnings[0]


def test_fields_of_an_unexpected_type_are_dropped(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path / "odd.json",
        {"mcpServers": {"odd": {"command": 42, "args": "not-a-list", "env": []}}},
    )

    result = parse_config_file(path)
    server = result.servers[0]

    assert server.command is None
    assert server.args == ()
    assert server.env_keys == ()
    assert server.transport == TRANSPORT_UNKNOWN
