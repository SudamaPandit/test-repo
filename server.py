"""Read-only MCP job discovery server; applications are not submitted."""
import os
from mcp.server.fastmcp import FastMCP
from jobfinder import search_jobs

mcp = FastMCP("Visa-Sponsored Data Engineering Jobs")

@mcp.tool()
def search_visa_sponsored_data_jobs(
    query: str = "senior data engineer",
    include_unverified: bool = False,
    max_results: int = 25,
) -> dict:
    """Find data engineering job leads in Europe and Australia (Queensland only).
    Sponsorship evidence remains unverified until checked on the employer site.
    No job applications are ever submitted by this server.
    """
    return search_jobs(query, include_unverified=include_unverified, max_results=max_results)

if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = int(os.getenv("PORT", "8000"))
    mcp.run(transport="streamable-http")
