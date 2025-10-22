"""
VELOX Dashboard - Simple Flask Web Interface
"""

from flask import Flask, render_template, jsonify
from datetime import datetime
import json
from pathlib import Path
import sys

# Add src to path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

app = Flask(__name__)

# Global state (will be updated by the system)
dashboard_state = {
    'system_status': 'Initializing',
    'is_running': False,
    'current_time': None,
    'strategies': [],
    'positions': [],
    'signals_today': 0,
    'orders_today': 0,
    'ticks_processed': 0,
    'account': {
        'capital': 100000,
        'pnl': 0,
        'pnl_pct': 0,
        'total_value': 100000
    },
    'recent_logs': [],
    'last_update': None
}


@app.route('/')
def index():
    """Serve the main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/status')
def get_status():
    """Get current system status."""
    dashboard_state['last_update'] = datetime.now().isoformat()
    return jsonify(dashboard_state)


@app.route('/api/strategies')
def get_strategies():
    """Get strategy information."""
    return jsonify({
        'strategies': dashboard_state.get('strategies', []),
        'count': len(dashboard_state.get('strategies', []))
    })


@app.route('/api/positions')
def get_positions():
    """Get current positions."""
    return jsonify({
        'positions': dashboard_state.get('positions', []),
        'count': len(dashboard_state.get('positions', []))
    })


@app.route('/api/account')
def get_account():
    """Get account information."""
    return jsonify(dashboard_state.get('account', {}))


def update_state(key, value):
    """Update dashboard state."""
    dashboard_state[key] = value


def add_log(message, level='INFO'):
    """Add a log entry."""
    log_entry = {
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'level': level,
        'message': message
    }
    
    # Keep only last 50 logs
    if 'recent_logs' not in dashboard_state:
        dashboard_state['recent_logs'] = []
    
    dashboard_state['recent_logs'].insert(0, log_entry)
    dashboard_state['recent_logs'] = dashboard_state['recent_logs'][:50]


def run_dashboard(host='0.0.0.0', port=5000, debug=False):
    """Run the dashboard server."""
    print(f"\n{'='*80}")
    print(f"🌐 VELOX Dashboard Starting")
    print(f"{'='*80}")
    print(f"📊 Dashboard URL: http://localhost:{port}")
    print(f"{'='*80}\n")
    
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == '__main__':
    run_dashboard(debug=True)
