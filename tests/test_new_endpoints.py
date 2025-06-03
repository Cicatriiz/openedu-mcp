"""
Tests for new stdio, HTTP, and SSE endpoints.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import AsyncGenerator

import httpx
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Fallback for anext (Python 3.10+)
try:
    # Check if anext is already available (Python 3.10+)
    anext
except NameError:
    # Define a fallback for Python 3.9
    async def anext_fallback(aiter):
        """
        Advances an asynchronous iterator and returns the next item.
        
        Equivalent to the built-in `anext` function introduced in Python 3.10.
        """
        return await aiter.__anext__()
    anext = anext_fallback

from main import (
    mcp,  # The FastMCP instance
    initialize_services,
    cleanup_services,
    handle_stdio_input,
    # stream_events, # This is a tool, but also an HTTP endpoint. How it's called matters.
    OpenEduMCPError # Assuming this is the correct exception
)
# If stream_events is directly callable as a tool for some reason, import it.
# Otherwise, it will be tested via HTTP.

# Attempt to get the ASGI app from mcp instance for httpx
# This is speculative. Common names are .app, .asgi_app, .server.app
ASGI_APP = getattr(mcp, "app", None) or getattr(mcp, "asgi_app", None)
if hasattr(mcp, "server") and mcp.server:
    ASGI_APP = ASGI_APP or getattr(mcp.server, "app", None)


# MockContext from existing integration tests
class MockContext:
    """Mock context for testing MCP tools."""
    def __init__(self, session_id: str = "test_session"):
        self.session_id = session_id
        # Add any other fields that tools might expect from the context
        self.user = None
        self.client_ip = "127.0.0.1"


@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for each test module."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def initialized_services() -> AsyncGenerator[None, None]:
    """Initialize and cleanup services once per module."""
    print("Initializing services for test module...")
    await initialize_services()
    print("Services initialized.")
    yield
    print("Cleaning up services...")
    await cleanup_services()
    print("Services cleaned up.")


# --- Test Stdio Endpoint ---
class TestStdioEndpoint:
    @pytest.mark.asyncio
    async def test_handle_stdio_basic_processing(self, initialized_services: None):
        ctx = MockContext()
        result = await handle_stdio_input(ctx, "hello world")
        assert result == "Processed: HELLO WORLD"

    @pytest.mark.asyncio
    async def test_handle_stdio_empty_input(self, initialized_services: None):
        ctx = MockContext()
        with pytest.raises(OpenEduMCPError, match="Input string cannot be empty"):
            await handle_stdio_input(ctx, "")

    @pytest.mark.asyncio
    async def test_handle_stdio_with_numbers_and_symbols(self, initialized_services: None):
        ctx = MockContext()
        result = await handle_stdio_input(ctx, "Test 123!@#")
        assert result == "Processed: TEST 123!@#"


# --- Test HTTP Interaction with Tools ---
# These tests depend on knowing how FastMCP exposes tools over HTTP.
# Common patterns: /mcp/<tool_name>, /tools/<tool_name>, or /rpc
# And the JSON RPC structure.
# For now, we assume a base_url and that httpx can connect if the server is run separately,
# OR if ASGI_APP is successfully found.

BASE_URL = "http://127.0.0.1:8000" # Default for Uvicorn if not configured otherwise in FastMCP

class TestHttpViaToolEndpoint:
    @pytest.mark.asyncio
    async def test_http_call_stdio_tool_directly(self, initialized_services: None):
        """
        This test assumes FastMCP exposes an ASGI app instance (mcp.app)
        that httpx can use directly. This is preferred over running a live server.
        """
        if not ASGI_APP:
            pytest.skip("ASGI app not found on MCP instance, skipping direct HTTP test.")

        async with httpx.AsyncClient(app=ASGI_APP, base_url="http://testserver") as client:
            # The URL and request format are assumptions about FastMCP's JSON RPC implementation
            # Option 1: JSON RPC style
            response = await client.post(
                "/mcp", # Assuming a single RPC endpoint
                json={
                    "jsonrpc": "2.0",
                    "method": "handle_stdio_input",
                    "params": {"input_string": "http test"},
                    "id": 1,
                },
            )
            # Option 2: Simpler tool call endpoint (if FastMCP uses this)
            # response = await client.post(
            #     "/tools/handle_stdio_input",
            #     json={"params": {"input_string": "http test"}}
            # )

            assert response.status_code == 200
            data = response.json()

            # Depending on JSON RPC spec, result might be under "result" or "data"
            if "result" in data: # Standard JSON RPC
                assert data["result"] == "Processed: HTTP TEST"
            elif "data" in data: # Other conventions
                 assert data["data"] == "Processed: HTTP TEST"
            else: # Or if it's a direct result not wrapped in JSON RPC success
                 assert data == "Processed: HTTP TEST"


    @pytest.mark.asyncio
    async def test_http_call_stdio_tool_empty_param_directly(self, initialized_services: None):
        if not ASGI_APP:
            pytest.skip("ASGI app not found on MCP instance, skipping direct HTTP test.")

        async with httpx.AsyncClient(app=ASGI_APP, base_url="http://testserver") as client:
            response = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "handle_stdio_input",
                    "params": {"input_string": ""}, # Empty string
                    "id": 2,
                },
            )
            # Expecting an error, but not a connection error.
            # The error should be from the tool's validation logic.
            assert response.status_code == 200 # JSON-RPC usually returns 200 for application errors
            data = response.json()
            assert "error" in data
            assert data["error"]["message"] == "Input string cannot be empty"
            # Or, if not JSON-RPC, it might be a 4xx/5xx error directly
            # assert response.status_code == 400 or response.status_code == 500


# --- Test SSE Endpoint (/events) ---
class TestSseEndpoint:
    @pytest.mark.asyncio
    async def test_sse_stream_connect_and_ping_directly(self, initialized_services: None):
        """
        Tests that the SSE endpoint at /events streams 'connected' and 'ping' events as expected.
        
        Connects to the Server-Sent Events endpoint, verifies the response status and content type,
        and asserts that both a 'connected' event with a success message and a 'ping' event with a
        heartbeat message are received in the correct format. Skips the test if the ASGI app is not available.
        """
        if not ASGI_APP:
            pytest.skip("ASGI app not found on MCP instance, skipping direct SSE test.")

        async with httpx.AsyncClient(app=ASGI_APP, base_url="http://testserver") as client:
            async with client.stream("GET", "/events") as response:
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/event-stream"

                events_received = 0
                expected_events = 2 # Connect + 1 ping

                stream_ended_prematurely = True
                async for line in response.aiter_lines():
                    # print(f"SSE Raw Line: {line}") # For debugging
                    if line.startswith("event: connected"):
                        events_received += 1
                        # Next line should be data for connected
                        data_line = await anext(response.aiter_lines())
                        # print(f"SSE Connected Data: {data_line}") # For debugging
                        assert data_line.startswith("data: ")
                        payload = json.loads(data_line[len("data: "):])
                        assert payload["message"] == "Successfully connected to SSE stream"

                    elif line.startswith("event: ping"):
                        events_received += 1
                        # Next line should be data for ping
                        data_line = await anext(response.aiter_lines())
                        # print(f"SSE Ping Data: {data_line}") # For debugging
                        assert data_line.startswith("data: ")
                        payload = json.loads(data_line[len("data: "):])
                        assert "heartbeat" in payload
                        assert payload["message"] == "ping"

                        # We've received enough events for the test
                        if events_received >= expected_events:
                            stream_ended_prematurely = False
                            break

                    # Handle empty lines between events
                    elif not line.strip():
                        continue

                assert not stream_ended_prematurely, f"Stream ended before receiving {expected_events} events."
                assert events_received >= expected_events

    # TODO: Add a test for SSE that handles client disconnection if possible,
    # but this is hard to simulate reliably with httpx without more control
    # over the exact timing of request cancellation.

if __name__ == "__main__":
    # This allows running the tests directly with `python tests/test_new_endpoints.py`
    # You might need to adjust for pytest specific features or run with `pytest tests/test_new_endpoints.py`
    pytest.main([__file__, "-v"])
