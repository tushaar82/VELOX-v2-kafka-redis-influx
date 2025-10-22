#!/usr/bin/env python3
"""
Quick diagnostic script to check data availability
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

if __name__ == "__main__":
    from src.adapters.data.historical import HistoricalDataManager
    
    hdm = HistoricalDataManager('./data')
    date = '2020-09-15'
    symbols = ['ABB', 'BATAINDIA', 'ANGELONE']
    
    print(f"\n{'='*80}")
    print(f"DATA DIAGNOSTIC FOR {date}")
    print(f"{'='*80}\n")
    
    df = hdm.get_data(date, symbols)
    
    print(f"Total rows loaded: {len(df)}")
    print(f"\nRows per symbol:")
    for symbol in symbols:
        symbol_df = df[df['symbol'] == symbol]
        print(f"  {symbol}: {len(symbol_df)} candles")
    
    ticks_per_candle = 10
    total_ticks = len(df) * ticks_per_candle
    print(f"\nWith {ticks_per_candle} ticks per candle:")
    print(f"  Total expected ticks: {total_ticks}")
    
    if not df.empty:
        print(f"\nTime range:")
        print(f"  Start: {df['timestamp'].min()}")
        print(f"  End: {df['timestamp'].max()}")
        
        print(f"\nFirst 5 candles:")
        print(df.head(5)[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']].to_string())
        
        print(f"\nLast 5 candles:")
        print(df.tail(5)[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']].to_string())
    else:
        print("\n❌ NO DATA FOUND!")
    
    print(f"\n{'='*80}\n")
