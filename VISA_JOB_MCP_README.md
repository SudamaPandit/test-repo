# Visa Job API / MCP (read-only)

This code was prepared from the uploaded user package. The running service is deployed from the isolated `visa-job-mcp` branch, so the original `main` branch is untouched.

- **Hosted MCP endpoint:** `https://visa-job-mcp-sudama.onrender.com/mcp`
- **Free, no-key feeds:** Arbeitnow Europe, Arbeitnow UK (errors are surfaced if unavailable), Sweden JobTech.
- **Optional keys:** Adzuna (Europe + Queensland, Australia), Reed UK, Jooble.
- **Run once locally:** `pip install -r requirements.txt && python cli.py --include-unverified --out jobs.json`
- **Serve locally:** `python server.py` and open the MCP endpoint using a compatible client.
- **Scope:** data engineering roles, Europe + Australia ONLY Queensland.
- **Important:** No application submission, resume upload, employer login or self-confirmed sponsorship. Employer statements and application eligibility require verification. No private secrets or CV stored.
- **Security:** No access control is currently configured. Before adding any paid/credentialled job API keys to Render, restrict MCP endpoint access and configure suitable authentication/rate-limiting. 
- **ChatGPT availability:** Direct custom MCP app setup depends on plan/workspace. The hosted server is NOT automatically attached to a ChatGPT chat or its scheduled tasks.

Original production guidance: https://modelcontextprotocol.io/
