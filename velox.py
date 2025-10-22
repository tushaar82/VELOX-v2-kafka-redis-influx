#!/usr/bin/env python3
"""
VELOX Trading System - Main Entry Point
Run this script from the project root directory.
"""

import sys
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

# Now run the system test which has proper imports
if __name__ == "__main__":
    # Import after path is set
    from run_system_test import run_quick_test
    import argparse
    
    parser = argparse.ArgumentParser(description='VELOX Multi-Strategy Trading System')
    parser.add_argument('--date', type=str, default='2020-09-15', 
                       help='Date to simulate (YYYY-MM-DD)')
    parser.add_argument('--speed', type=float, default=1000.0, 
                       help='Simulation speed multiplier')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("🚀 VELOX MULTI-STRATEGY TRADING SYSTEM")
    print("="*80 + "\n")
    
    success = run_quick_test(date=args.date, speed=args.speed)
    
    if success:
        print("\n" + "="*80)
        print("✅ VELOX SYSTEM RAN SUCCESSFULLY")
        print("="*80 + "\n")
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print("❌ VELOX SYSTEM ENCOUNTERED ERRORS")
        print("="*80 + "\n")
        sys.exit(1)
