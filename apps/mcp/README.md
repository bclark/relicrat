# RelicRat read-only MCP server

This optional client connects to your private RelicRat API over HTTPS or a
numeric loopback address. Your MCP host starts the process over stdio. The
adapter has no listener, database access, provider calls, or RelicRat account
requirement. The core server runs independently of the adapter.

1. On a machine running a trusted MCP host, install Python 3.10 or newer and
   install the adapter dependencies in a dedicated environment.

   ```sh
   python3 -m venv .venv-mcp
   .venv-mcp/bin/python -m pip install -r apps/mcp/requirements.txt
   ```

2. Issue a read-only credential through the [private agent API](../api/INVENTORY.md#read-only-agent-api).
   Use the private API origin reachable from the MCP host. The standard web
   origin does not forward these routes. For an operator-managed Compose install
   without a reachable API origin, use a local Compose override that binds the
   API only to the server's loopback interface, then run the MCP host there or
   forward that port over SSH. Keep the API private.

3. Configure the MCP host to launch the following command over stdio, using
   absolute paths in its configuration. Pass `RELICRAT_API_ORIGIN` (for example,
   `http://127.0.0.1:8000`) and `RELICRAT_AGENT_TOKEN` in the process environment.
   Use the host's secret storage for the token.

   ```sh
   /path/to/.venv-mcp/bin/python /path/to/relicrat/apps/mcp/server.py
   ```

The tools are `search_collection`, `get_copy_location`, and
`list_unresolved_audit_findings`. The list tools return a page at a time. Use
only an agent host you trust with collection data. A hosted model may receive
the tool results if your MCP host sends them there. Revoke the credential from
RelicRat to stop future reads.

CI runs `smoke_test.py` against a disposable API at `127.0.0.1:8000` with
synthetic records. The test issues and revokes the active credential, so use
it only with a disposable test API.
