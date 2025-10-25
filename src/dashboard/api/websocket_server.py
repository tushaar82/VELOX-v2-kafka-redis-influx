"""
WebSocket server for real-time dashboard updates
Streams position updates, price changes, and trade events
"""
import asyncio
import json
import logging
from typing import Dict, Set, Any
from datetime import datetime
from dataclasses import asdict
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .data_service import DataService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.symbol_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)

        # Remove from symbol subscriptions
        for subscribers in self.symbol_subscriptions.values():
            subscribers.discard(websocket)

        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_to_symbol_subscribers(self, symbol: str, message: dict):
        """Broadcast message to clients subscribed to a symbol"""
        if symbol not in self.symbol_subscriptions:
            return

        disconnected = set()

        for connection in self.symbol_subscriptions[symbol]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to symbol subscriber: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.symbol_subscriptions[symbol].discard(connection)

    def subscribe_to_symbol(self, symbol: str, websocket: WebSocket):
        """Subscribe client to symbol updates"""
        if symbol not in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol] = set()

        self.symbol_subscriptions[symbol].add(websocket)
        logger.info(f"Client subscribed to {symbol}")

    def unsubscribe_from_symbol(self, symbol: str, websocket: WebSocket):
        """Unsubscribe client from symbol updates"""
        if symbol in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol].discard(websocket)


class DashboardWebSocketServer:
    """WebSocket server for dashboard real-time updates"""

    def __init__(self, data_service: DataService):
        self.app = FastAPI(title="VELOX Dashboard WebSocket API")
        self.data_service = data_service
        self.manager = ConnectionManager()
        self.redis_client = None
        self.pubsub = None
        self.is_running = False

        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup WebSocket and HTTP routes"""

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """Main WebSocket endpoint"""
            await self.manager.connect(websocket)

            try:
                # Send initial data
                await self._send_initial_data(websocket)

                # Listen for client messages
                while True:
                    data = await websocket.receive_json()
                    await self._handle_client_message(websocket, data)

            except WebSocketDisconnect:
                self.manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.manager.disconnect(websocket)

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "connections": len(self.manager.active_connections)
            }

    async def _send_initial_data(self, websocket: WebSocket):
        """Send initial dashboard data to newly connected client"""
        try:
            # Get all open positions
            positions = self.data_service.get_open_positions()
            await self.manager.send_personal_message({
                "type": "initial_positions",
                "data": [asdict(pos) for pos in positions]
            }, websocket)

            # Get recent closed trades
            closed_trades = self.data_service.get_closed_trades(limit=50)
            await self.manager.send_personal_message({
                "type": "initial_closed_trades",
                "data": [asdict(trade) for trade in closed_trades]
            }, websocket)

            # Get strategy metrics
            metrics = self.data_service.get_all_strategy_metrics()
            await self.manager.send_personal_message({
                "type": "initial_strategy_metrics",
                "data": {k: asdict(v) for k, v in metrics.items()}
            }, websocket)

            # Get system status
            status = self.data_service.get_system_status()
            await self.manager.send_personal_message({
                "type": "system_status",
                "data": status
            }, websocket)

        except Exception as e:
            logger.error(f"Error sending initial data: {e}")

    async def _handle_client_message(self, websocket: WebSocket, message: dict):
        """Handle incoming client messages"""
        msg_type = message.get("type")

        if msg_type == "subscribe_symbol":
            symbol = message.get("symbol")
            if symbol:
                self.manager.subscribe_to_symbol(symbol, websocket)

                # Send price history for the symbol
                price_history = self.data_service.get_price_history(symbol, hours=1)
                await self.manager.send_personal_message({
                    "type": "price_history",
                    "symbol": symbol,
                    "data": [asdict(p) for p in price_history]
                }, websocket)

        elif msg_type == "unsubscribe_symbol":
            symbol = message.get("symbol")
            if symbol:
                self.manager.unsubscribe_from_symbol(symbol, websocket)

        elif msg_type == "get_position":
            symbol = message.get("symbol")
            if symbol:
                position = self.data_service.get_position_by_symbol(symbol)
                await self.manager.send_personal_message({
                    "type": "position_update",
                    "symbol": symbol,
                    "data": asdict(position) if position else None
                }, websocket)

        elif msg_type == "ping":
            await self.manager.send_personal_message({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }, websocket)

    async def _redis_listener(self):
        """Listen to Redis pub/sub for real-time updates"""
        try:
            self.redis_client = await aioredis.from_url(
                "redis://localhost:6379",
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()

            # Subscribe to relevant channels
            await self.pubsub.subscribe(
                "position_updates",
                "trade_closed",
                "price_updates",
                "trailing_sl_updates"
            )

            logger.info("Subscribed to Redis pub/sub channels")

            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    await self._handle_redis_message(message)

        except Exception as e:
            logger.error(f"Redis listener error: {e}")
        finally:
            if self.pubsub:
                await self.pubsub.unsubscribe()
            if self.redis_client:
                await self.redis_client.close()

    async def _handle_redis_message(self, message: dict):
        """Handle messages from Redis pub/sub"""
        try:
            channel = message["channel"]
            data = json.loads(message["data"])

            if channel == "position_updates":
                # Broadcast position update
                await self.manager.broadcast({
                    "type": "position_update",
                    "data": data
                })

            elif channel == "trade_closed":
                # Broadcast trade closure
                await self.manager.broadcast({
                    "type": "trade_closed",
                    "data": data
                })

            elif channel == "price_updates":
                # Broadcast to symbol subscribers
                symbol = data.get("symbol")
                if symbol:
                    await self.manager.broadcast_to_symbol_subscribers(symbol, {
                        "type": "price_update",
                        "symbol": symbol,
                        "data": data
                    })

            elif channel == "trailing_sl_updates":
                # Broadcast trailing SL update
                await self.manager.broadcast({
                    "type": "trailing_sl_update",
                    "data": data
                })

        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")

    async def _periodic_updates(self):
        """Send periodic updates to all clients"""
        while self.is_running:
            try:
                # Update positions every 1 second
                positions = self.data_service.get_open_positions()
                await self.manager.broadcast({
                    "type": "positions_snapshot",
                    "data": [asdict(pos) for pos in positions],
                    "timestamp": datetime.now().isoformat()
                })

                # Update system status every 5 seconds
                await asyncio.sleep(5)
                status = self.data_service.get_system_status()
                await self.manager.broadcast({
                    "type": "system_status",
                    "data": status
                })

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in periodic updates: {e}")
                await asyncio.sleep(1)

    async def start_background_tasks(self):
        """Start background tasks"""
        self.is_running = True

        # Start Redis listener
        asyncio.create_task(self._redis_listener())

        # Start periodic updates
        asyncio.create_task(self._periodic_updates())

        logger.info("Background tasks started")

    def run(self, host: str = "0.0.0.0", port: int = 8765):
        """Run the WebSocket server"""
        logger.info(f"Starting WebSocket server on {host}:{port}")

        @self.app.on_event("startup")
        async def startup():
            await self.start_background_tasks()

        @self.app.on_event("shutdown")
        async def shutdown():
            self.is_running = False
            if self.redis_client:
                await self.redis_client.close()

        uvicorn.run(self.app, host=host, port=port)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create data service
    data_service = DataService()

    # Create and run WebSocket server
    server = DashboardWebSocketServer(data_service)
    server.run()
