"""
REST API for VELOX Analytics Dashboard
Provides endpoints for historical data, analytics, and diagnostics
"""
import logging
from typing import Optional, List
from datetime import datetime
from dataclasses import asdict
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .data_service import DataService

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="VELOX Analytics Dashboard API",
    description="Professional trading analytics and monitoring API",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data service
data_service = DataService()


# ========== HEALTH & STATUS ==========

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "VELOX Analytics Dashboard API",
        "version": "2.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = data_service.get_system_status()
    return {
        "status": "healthy" if all(status['databases'].values()) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "databases": status['databases']
    }


@app.get("/api/status")
async def get_status():
    """Get overall system status"""
    return data_service.get_system_status()


# ========== POSITIONS ==========

@app.get("/api/positions")
async def get_positions():
    """Get all open positions"""
    positions = data_service.get_open_positions()
    return {
        "count": len(positions),
        "positions": [asdict(pos) for pos in positions],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/positions/{symbol}")
async def get_position(symbol: str, strategy_id: Optional[str] = None):
    """Get position for specific symbol"""
    position = data_service.get_position_by_symbol(symbol, strategy_id)

    if not position:
        raise HTTPException(status_code=404, detail=f"Position not found for {symbol}")

    return {
        "position": asdict(position),
        "timestamp": datetime.now().isoformat()
    }


# ========== TRADES ==========

@app.get("/api/trades/closed")
async def get_closed_trades(
    limit: int = Query(100, ge=1, le=1000),
    strategy_id: Optional[str] = None
):
    """Get closed trades with optional filtering"""
    trades = data_service.get_closed_trades(limit=limit, strategy_id=strategy_id)

    return {
        "count": len(trades),
        "trades": [asdict(trade) for trade in trades],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/trades/unclosed")
async def get_unclosed_orders():
    """Get orders that might not be properly closed"""
    unclosed = data_service.get_unclosed_orders()

    return {
        "count": len(unclosed),
        "unclosed_orders": unclosed,
        "timestamp": datetime.now().isoformat()
    }


# ========== STRATEGY METRICS ==========

@app.get("/api/strategies")
async def get_all_strategies():
    """Get all strategy metrics"""
    metrics = data_service.get_all_strategy_metrics()

    return {
        "count": len(metrics),
        "strategies": {k: asdict(v) for k, v in metrics.items()},
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/strategies/{strategy_id}")
async def get_strategy_metrics(strategy_id: str):
    """Get metrics for specific strategy"""
    metrics = data_service.get_strategy_metrics(strategy_id)

    if not metrics:
        raise HTTPException(status_code=404, detail=f"No metrics found for strategy {strategy_id}")

    return {
        "strategy": asdict(metrics),
        "timestamp": datetime.now().isoformat()
    }


# ========== PRICE & CHART DATA ==========

@app.get("/api/price/{symbol}")
async def get_price_history(
    symbol: str,
    hours: int = Query(1, ge=1, le=24)
):
    """Get price history for symbol"""
    prices = data_service.get_price_history(symbol, hours=hours)

    return {
        "symbol": symbol,
        "count": len(prices),
        "prices": [asdict(p) for p in prices],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/indicators/{symbol}/{strategy_id}")
async def get_indicators(symbol: str, strategy_id: str):
    """Get current indicator values"""
    indicators = data_service.get_indicator_values(symbol, strategy_id)

    return {
        "symbol": symbol,
        "strategy_id": strategy_id,
        "indicators": indicators,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/trailing-sl/{trade_id}")
async def get_trailing_sl_history(trade_id: str):
    """Get trailing stop-loss history for a trade"""
    sl_history = data_service.get_trailing_sl_history(trade_id)

    return {
        "trade_id": trade_id,
        "count": len(sl_history),
        "history": sl_history,
        "timestamp": datetime.now().isoformat()
    }


# ========== ANALYTICS ==========

@app.get("/api/analytics/summary")
async def get_analytics_summary():
    """Get comprehensive analytics summary"""
    positions = data_service.get_open_positions()
    closed_trades = data_service.get_closed_trades(limit=100)
    strategy_metrics = data_service.get_all_strategy_metrics()
    system_status = data_service.get_system_status()

    # Calculate summary metrics
    total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
    total_realized_pnl = sum(trade.pnl for trade in closed_trades)
    total_pnl = total_unrealized_pnl + total_realized_pnl

    winning_trades = sum(1 for trade in closed_trades if trade.pnl > 0)
    losing_trades = sum(1 for trade in closed_trades if trade.pnl <= 0)
    total_closed = len(closed_trades)
    win_rate = (winning_trades / total_closed * 100) if total_closed > 0 else 0

    return {
        "summary": {
            "open_positions": len(positions),
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_realized_pnl": total_realized_pnl,
            "total_pnl": total_pnl,
            "closed_trades": total_closed,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate
        },
        "strategies": {k: asdict(v) for k, v in strategy_metrics.items()},
        "system_status": system_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/analytics/performance")
async def get_performance_analysis():
    """Get detailed performance analysis"""
    closed_trades = data_service.get_closed_trades(limit=500)

    if not closed_trades:
        return {
            "error": "No closed trades found",
            "timestamp": datetime.now().isoformat()
        }

    # Performance metrics
    total_trades = len(closed_trades)
    winners = [t for t in closed_trades if t.pnl > 0]
    losers = [t for t in closed_trades if t.pnl <= 0]

    total_win = sum(t.pnl for t in winners)
    total_loss = sum(abs(t.pnl) for t in losers)

    avg_win = total_win / len(winners) if winners else 0
    avg_loss = total_loss / len(losers) if losers else 0

    profit_factor = total_win / total_loss if total_loss > 0 else 0
    win_rate = (len(winners) / total_trades * 100) if total_trades > 0 else 0

    # Calculate expectancy
    expectancy = (avg_win * len(winners) - avg_loss * len(losers)) / total_trades if total_trades > 0 else 0

    # Group by symbol
    symbol_performance = {}
    for trade in closed_trades:
        if trade.symbol not in symbol_performance:
            symbol_performance[trade.symbol] = {
                'trades': 0,
                'wins': 0,
                'total_pnl': 0
            }

        symbol_performance[trade.symbol]['trades'] += 1
        symbol_performance[trade.symbol]['total_pnl'] += trade.pnl
        if trade.pnl > 0:
            symbol_performance[trade.symbol]['wins'] += 1

    # Add win rates
    for symbol in symbol_performance:
        perf = symbol_performance[symbol]
        perf['win_rate'] = (perf['wins'] / perf['trades'] * 100) if perf['trades'] > 0 else 0

    # Exit reason analysis
    exit_reasons = {}
    for trade in closed_trades:
        reason = trade.exit_reason
        if reason not in exit_reasons:
            exit_reasons[reason] = {'count': 0, 'total_pnl': 0}

        exit_reasons[reason]['count'] += 1
        exit_reasons[reason]['total_pnl'] += trade.pnl

    return {
        "overall": {
            "total_trades": total_trades,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "total_pnl": sum(t.pnl for t in closed_trades)
        },
        "by_symbol": symbol_performance,
        "by_exit_reason": exit_reasons,
        "timestamp": datetime.now().isoformat()
    }


# ========== DIAGNOSTICS ==========

@app.get("/api/diagnostics/verify-orders")
async def verify_order_closure():
    """Verify all orders are properly closed"""
    unclosed = data_service.get_unclosed_orders()

    return {
        "status": "ok" if len(unclosed) == 0 else "warning",
        "unclosed_count": len(unclosed),
        "unclosed_orders": unclosed,
        "message": "All orders closed" if len(unclosed) == 0 else f"{len(unclosed)} orders may be unclosed",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/diagnostics/database-health")
async def check_database_health():
    """Check database connectivity and health"""
    status = data_service.get_system_status()

    db_status = status['databases']
    all_healthy = all(db_status.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "databases": {
            "redis": {
                "connected": db_status['redis'],
                "status": "operational" if db_status['redis'] else "unavailable"
            },
            "influxdb": {
                "connected": db_status['influxdb'],
                "status": "operational" if db_status['influxdb'] else "unavailable"
            },
            "sqlite": {
                "connected": db_status['sqlite'],
                "status": "operational" if db_status['sqlite'] else "unavailable"
            }
        },
        "timestamp": datetime.now().isoformat()
    }


# ========== ERROR HANDLERS ==========

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# ========== STARTUP & SHUTDOWN ==========

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("VELOX Analytics Dashboard API starting...")
    logger.info("Data service initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("VELOX Analytics Dashboard API shutting down...")
    data_service.close()


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the REST API server"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info(f"Starting REST API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
