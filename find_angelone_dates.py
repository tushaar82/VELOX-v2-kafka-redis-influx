#!/usr/bin/env python3
"""Find dates where ANGELONE has data"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

if __name__ == "__main__":
    from src.adapters.data.historical import HistoricalDataManager
    
    hdm = HistoricalDataManager('./data')
    
    # Check what symbols we have
    stats = hdm.get_statistics()
    print(f"\n{'='*80}")
    print("AVAILABLE SYMBOLS")
    print(f"{'='*80}\n")
    
    print(f"Symbols: {stats['symbols']}")
    print(f"Total files: {stats.get('total_files', 'N/A')}")
    print()
    
    # Try different dates to find one with ANGELONE data
    test_dates = ['2024-01-02', '2023-01-02', '2022-01-03', '2021-01-04']
    
    for test_date in test_dates:
        print(f"\n{'='*80}")
        print(f"TESTING DATE: {test_date}")
        print(f"{'='*80}\n")
        
        symbols = ['ABB', 'BATAINDIA', 'ANGELONE']
        df = hdm.get_data(test_date, symbols)
        
        print(f"Total rows: {len(df)}")
        for symbol in symbols:
            symbol_df = df[df['symbol'] == symbol]
            print(f"  {symbol}: {len(symbol_df)} candles")
        
        # Check if ANGELONE has data
        angelone_df = df[df['symbol'] == 'ANGELONE']
        if len(angelone_df) > 0:
            print(f"\n✅ Found date with ANGELONE data: {test_date}")
            break
    
    print(f"\n{'='*80}\n")
