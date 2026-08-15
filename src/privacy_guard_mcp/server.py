from __future__ import annotations

from privacy_guard.guard import Guard
from privacy_guard.types import MappingExpired, SanitizeResult

guard = Guard()

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # mcp 2.x
    from mcp.server import MCPServer as FastMCP  # type: ignore[assignment]

mcp = FastMCP("privacy-guard")


@mcp.tool()
def sanitize(text: str) -> dict[str, str]:
    """Replace Sensitive Spans with typed Placeholders. Returns Safe Text and a Mapping Id."""
    result: SanitizeResult = guard.sanitize(text)
    return {"safe_text": result.safe_text, "mapping_id": result.mapping_id}


@mcp.tool()
def restore(text: str, mapping_id: str) -> dict[str, str]:
    """Substitute real values back into text that still contains Placeholders."""
    try:
        restored = guard.restore(text, mapping_id)
    except MappingExpired as exc:
        return {"restored_text": "", "error": f"mapping expired: {exc}"}
    return {"restored_text": restored}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
