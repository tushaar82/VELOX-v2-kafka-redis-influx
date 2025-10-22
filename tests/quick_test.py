"""
Quick test to verify basic functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging_config import initialize_logging
from src.adapters.data.historical import HistoricalDataManager
import logging

def main():
    """Quick test."""
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== VELOX Quick Test ===\n")
    
    # Test 1: Data loading
    print("1. Testing data loading...")
    hdm = HistoricalDataManager('./data')
    stats = hdm.get_statistics()
    
    print(f"   Symbols found: {len(stats['symbols'])}")
    print(f"   Symbols: {', '.join(stats['symbols'][:5])}")
    
    if stats['symbols']:
        symbol = stats['symbols'][0]
        dates = hdm.get_available_dates(symbol)
        print(f"\n   {symbol}:")
        print(f"   - Trading days: {len(dates)}")
        print(f"   - Date range: {dates[0]} to {dates[-1]}")
        
        # Load a sample date
        if len(dates) > 100:
            test_date = dates[100]
            print(f"\n2. Loading data for {test_date}...")
            df = hdm.get_data(test_date, [symbol])
            print(f"   Rows loaded: {len(df)}")
            print(f"\n   Sample data:")
            print(df.head(3).to_string())
            
            print("\n✓ All tests passed!")
        else:
            print("\n⚠ Not enough dates for full test")
    else:
        print("\n✗ No symbols found")

if __name__ == "__main__":
    main()
