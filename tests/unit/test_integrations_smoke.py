from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from dashboard.integrations.base import (
    ToolIntegrationError,
    ToolKey,
    collect_tool_diagnostics,
    register_tool_import_paths,
    resolve_tool_root,
)


def test_resolve_tool_root_uses_expected_structure(tmp_path: Path) -> None:
    expected = tmp_path / "tools" / "1067-relelisten-extraktor"

    resolved = resolve_tool_root(ToolKey.RELE_1067, workspace_root=tmp_path)

    assert resolved == expected


def test_resolve_tool_root_rejects_unknown_tool(tmp_path: Path) -> None:
    with pytest.raises(ToolIntegrationError):
        resolve_tool_root("unknown", workspace_root=tmp_path)


def test_register_tool_import_paths_for_1052_adds_src_and_root(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    tool_root = tmp_path / "tools" / "1052-buchungsimporteur-sap-lbv"
    src_path = tool_root / "src"
    src_path.mkdir(parents=True)
    monkeypatch.setattr(sys, "path", [])

    register_tool_import_paths(ToolKey.IMPORT_1052, workspace_root=tmp_path)

    assert sys.path[0] == str(src_path)
    assert str(tool_root) in sys.path


def test_register_tool_import_paths_raises_for_missing_tool_directory(
    tmp_path: Path,
) -> None:
    with pytest.raises(ToolIntegrationError):
        register_tool_import_paths(ToolKey.PDF_1049, workspace_root=tmp_path)


def test_collect_tool_diagnostics_marks_missing_tools(tmp_path: Path) -> None:
    diagnostics = collect_tool_diagnostics(workspace_root=tmp_path)

    assert len(diagnostics) == 3
    assert all(diagnostic.tool_available is False for diagnostic in diagnostics)
    assert all(diagnostic.import_available is False for diagnostic in diagnostics)
