from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ToolIntegrationError(RuntimeError):
    """Fehler bei der Integration eines vendorten Tool-Moduls."""


class ToolKey(StrEnum):
    PDF_1049 = "1049"
    RELE_1067 = "1067"
    IMPORT_1052 = "1052"


@dataclass(slots=True, frozen=True)
class BinaryArtifact:
    file_name: str
    payload: bytes
    mime_type: str


@dataclass(slots=True, frozen=True)
class ToolDiagnostic:
    tool: ToolKey
    display_name: str
    path: Path
    tool_available: bool
    import_available: bool
    detail: str


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
TOOLS_ROOT = WORKSPACE_ROOT / "tools"

_TOOL_DIRECTORY_NAMES = {
    ToolKey.PDF_1049: "1049-pdf-extraktor-lbv",
    ToolKey.RELE_1067: "1067-relelisten-extraktor",
    ToolKey.IMPORT_1052: "1052-buchungsimporteur-sap-lbv",
}

_TOOL_DISPLAY_NAMES = {
    ToolKey.PDF_1049: "1049 PDF-Extraktor",
    ToolKey.RELE_1067: "1067 RELElisten-Extraktor",
    ToolKey.IMPORT_1052: "1052 Buchungsimporteur",
}

_TOOL_MODULE_NAMES = {
    ToolKey.PDF_1049: "main",
    ToolKey.RELE_1067: "relelisten_extraktor",
    ToolKey.IMPORT_1052: "buchungsimporteur",
}


def resolve_tool_root(tool: ToolKey | str, workspace_root: Path | None = None) -> Path:
    try:
        tool_key = ToolKey(tool)
    except ValueError as exc:
        raise ToolIntegrationError(f"Unbekannter Tool-Schlüssel: {tool}") from exc

    root = workspace_root or WORKSPACE_ROOT
    return root / "tools" / _TOOL_DIRECTORY_NAMES[tool_key]


def register_tool_import_paths(
    tool: ToolKey | str, workspace_root: Path | None = None
) -> Path:
    tool_root = resolve_tool_root(tool, workspace_root=workspace_root)
    tool_key = ToolKey(tool)
    if not tool_root.exists():
        raise ToolIntegrationError(f"Tool-Verzeichnis fehlt: {tool_root}")

    candidates: list[Path]
    if tool_key == ToolKey.IMPORT_1052:
        src_path = tool_root / "src"
        if not src_path.exists():
            raise ToolIntegrationError(
                f"Erwartetes src-Verzeichnis fehlt für 1052: {src_path}"
            )
        candidates = [src_path, tool_root]
    else:
        candidates = [tool_root]

    for path in reversed(candidates):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    return tool_root


def collect_tool_diagnostics(
    workspace_root: Path | None = None,
) -> list[ToolDiagnostic]:
    return [
        diagnose_tool(tool_key, workspace_root=workspace_root) for tool_key in ToolKey
    ]


def diagnose_tool(
    tool: ToolKey,
    workspace_root: Path | None = None,
) -> ToolDiagnostic:
    tool_root = resolve_tool_root(tool, workspace_root=workspace_root)
    try:
        active_root = register_tool_import_paths(tool, workspace_root=workspace_root)
    except ToolIntegrationError as exc:
        return ToolDiagnostic(
            tool=tool,
            display_name=_TOOL_DISPLAY_NAMES[tool],
            path=tool_root,
            tool_available=tool_root.exists(),
            import_available=False,
            detail=str(exc),
        )

    module_name = _TOOL_MODULE_NAMES[tool]
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        return ToolDiagnostic(
            tool=tool,
            display_name=_TOOL_DISPLAY_NAMES[tool],
            path=active_root,
            tool_available=True,
            import_available=False,
            detail=f"Import fehlgeschlagen: {exc}",
        )

    return ToolDiagnostic(
        tool=tool,
        display_name=_TOOL_DISPLAY_NAMES[tool],
        path=active_root,
        tool_available=True,
        import_available=True,
        detail="Bereit.",
    )
