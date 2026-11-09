"""Native Python launcher using official MCP transports, without product logic."""

import argparse
import logging
import os
import signal
import sys
from urllib.parse import urlsplit

import anyio
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server.stdio import stdio_server
from mcp.shared.message import ClientMessageMetadata, SessionMessage

from chans_mcp import __version__


def configuration(environ=None):
    env = os.environ if environ is None else environ
    key = env.get("CHANS_API_KEY", "").strip()
    if not key or "\r" in key or "\n" in key:
        raise ValueError("Set CHANS_API_KEY to a valid Chans API key.")
    url = env.get("CHANS_MCP_URL", "https://api.chans.ai/mcp/")
    try:
        parsed = urlsplit(url)
        _ = parsed.port
        valid = (
            parsed.hostname
            and (
                parsed.scheme == "https"
                or (
                    parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
                )
            )
            and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
            and not any(character.isspace() for character in url)
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(
            "CHANS_MCP_URL requires HTTPS (HTTP is allowed on loopback), without credentials, query or fragment."
        )
    return url, key


def http_client(key):
    return httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {key}"},
        timeout=httpx2.Timeout(300, connect=15),
        follow_redirects=False,
    )


async def doctor(url, key):
    async with http_client(key) as http:
        async with Client(streamable_http_client(url, http_client=http), mode="legacy") as client:
            count = 0
            cursor = None
            while True:
                page = await client.list_tools(cursor=cursor)
                count += len(page.tools)
                cursor = page.next_cursor
                if not cursor:
                    break
            print(
                f"Chans MCP connected; {count} authorized tools available. No tools executed.",
                file=sys.stderr,
            )


async def bridge(url, key):
    # No local Server/Client session: the host and remote server negotiate directly.
    # SDK transports own framing, HTTP sessions, SSE and cancellation delivery.
    version = None
    initialize_id = None
    async with anyio.create_task_group() as tasks:
        old_handlers = {}
        for number in (signal.SIGINT, signal.SIGTERM):
            old_handlers[number] = signal.signal(number, lambda *_: tasks.cancel_scope.cancel())
        try:
            async with http_client(key) as http:
                async with streamable_http_client(url, http_client=http) as (
                    remote_read,
                    remote_write,
                ):
                    async with stdio_server() as (local_read, local_write):

                        async def upstream():
                            nonlocal initialize_id
                            async for item in local_read:
                                if isinstance(item, Exception):
                                    raise ValueError("Invalid stdio protocol message")
                                message = item.message
                                if getattr(message, "method", None) == "initialize":
                                    initialize_id = message.id
                                metadata = ClientMessageMetadata(
                                    headers={"mcp-protocol-version": version} if version else None
                                )
                                await remote_write.send(SessionMessage(message, metadata))
                            tasks.cancel_scope.cancel()

                        async def downstream():
                            nonlocal version
                            async for item in remote_read:
                                if isinstance(item, Exception):
                                    raise item
                                message = item.message
                                result = getattr(message, "result", None)
                                if getattr(message, "id", None) == initialize_id and isinstance(
                                    result, dict
                                ):
                                    version = result.get("protocolVersion", version)
                                await local_write.send(item)
                            tasks.cancel_scope.cancel()

                        tasks.start_soon(upstream)
                        tasks.start_soon(downstream)
                        await anyio.sleep_forever()
        finally:
            for number, handler in old_handlers.items():
                signal.signal(number, handler)


def main():
    parser = argparse.ArgumentParser(
        description="Chans MCP stdio bridge. Set CHANS_API_KEY; optionally CHANS_MCP_URL."
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("command", nargs="?", choices=["doctor"])
    args = parser.parse_args()
    # Third-party errors may embed URLs or headers. Only our sanitized diagnostics
    # reach stderr; stdout belongs exclusively to the stdio transport.
    logging.disable(logging.CRITICAL)
    try:
        config = configuration()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    try:
        anyio.run(doctor if args.command == "doctor" else bridge, *config)
    except KeyboardInterrupt:
        return 0
    except Exception:
        print(
            "Chans MCP connection failed. Check credentials, endpoint and connectivity. Check operation status before retrying an interrupted tool call.",
            file=sys.stderr,
        )
        return 1
    return 0
