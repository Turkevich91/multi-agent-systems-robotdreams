import asyncio
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastmcp import FastMCP

from config import settings
from shared_tools import output_dir_info, save_report_impl


mcp = FastMCP(name="ReportMCP")


@mcp.tool
def save_report(filename: str, content: str) -> str:
    """Save the final Markdown research report into the local output directory."""
    return save_report_impl(filename, content)


@mcp.resource("resource://output-dir")
def output_dir_resource() -> str:
    """Output directory path and saved Markdown reports."""
    return json.dumps(output_dir_info(), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print(f"ReportMCP running at {settings.report_mcp_url}")
    asyncio.run(
        mcp.run_async(
            transport="streamable-http",
            host=settings.host,
            port=settings.report_mcp_port,
        )
    )
