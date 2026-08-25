"""Tests for WebSocket connection management and tool updates."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from websocket import ConnectionManager, reset_active_connection, send_tool_update, set_active_connection


class FakeWebSocket:
    def __init__(self):
        self.accept = AsyncMock()
        self.send_json = AsyncMock()


class ConnectionManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_connect_accepts_and_tracks_connection(self):
        manager = ConnectionManager()
        websocket = FakeWebSocket()

        await manager.connect(websocket)

        websocket.accept.assert_awaited_once()
        self.assertIn(websocket, manager.connections)
        self.assertIsNotNone(manager.loop)

    async def test_disconnect_removes_connection(self):
        manager = ConnectionManager()
        websocket = FakeWebSocket()
        await manager.connect(websocket)

        manager.disconnect(websocket)
        manager.disconnect(websocket)

        self.assertNotIn(websocket, manager.connections)

    async def test_broadcast_sends_to_all_connections(self):
        manager = ConnectionManager()
        first = FakeWebSocket()
        second = FakeWebSocket()
        await manager.connect(first)
        await manager.connect(second)

        await manager.broadcast({"type": "status", "content": "working"})

        first.send_json.assert_awaited_once_with({"type": "status", "content": "working"})
        second.send_json.assert_awaited_once_with({"type": "status", "content": "working"})


class ToolUpdateTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_tool_update_sends_expected_event(self):
        manager = ConnectionManager()
        websocket = FakeWebSocket()
        await manager.connect(websocket)
        token = set_active_connection(websocket)
        try:
            with patch("websocket.asyncio.run_coroutine_threadsafe") as schedule:
                send_tool_update("retrieving documents")

                schedule.assert_called_once()
                coroutine, loop = schedule.call_args.args
                self.assertIs(loop, manager.loop)
                coroutine.close()
                self.assertIsInstance(coroutine, type(asyncio.sleep(0)))
        finally:
            reset_active_connection(token)


if __name__ == "__main__":
    unittest.main()
