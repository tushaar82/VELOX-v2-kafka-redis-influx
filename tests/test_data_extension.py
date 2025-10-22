#!/usr/bin/env python3
"""Test if data extension is working."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import pandas as pd
from src.adapters.data.historical import HistoricalDataManager

# Initialize
data_manager = HistoricalDataManager('./data')
date = '2020-09-15'
symbols = ['ABB', 'ADANIENT', 'AMBER', 'BANKINDIA', 'BATAINDIA']

print(f"\n{'='*80}")
print(f"Testing Data Extension for {date}")
print(f"{'='*80}\n")

# Load 1-minute data
df_1min = data_manager.get_data(date, symbols)
print(f"1-minute data loaded: {len(df_1min)} rows")
print(f"Time range: {df_1min['timestamp'].min()} to {df_1min['timestamp'].max()}")
print(f"Symbols: {df_1min['symbol'].unique()}")

# Resample to 3-minute with extension
df_list = []
for symbol in symbols:
    symbol_data = df_1min[df_1min['symbol'] == symbol].copy()
    if not symbol_data.empty:
        print(f"\n{symbol}:")
        print(f"  Original 1-min rows: {len(symbol_data)}")
        print(f"  Time range: {symbol_data['timestamp'].min()} to {symbol_data['timestamp'].max()}")
        
        symbol_data.set_index('timestamp', inplace=True)
        
        # Resample to 3-minute OHLC
        resampled = symbol_data.resample('3T').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        print(f"  After 3-min resample: {len(resampled)} rows")
        
        # Ensure we run until 15:15 by creating a full 3-minute index and filling gaps
        market_open = pd.Timestamp(f"{date} 09:15:00")
        market_cutoff = pd.Timestamp(f"{date} 15:15:00")
        full_idx = pd.date_range(start=market_open, end=market_cutoff, freq='3T')
        
        print(f"  Full index should have: {len(full_idx)} rows (09:15 to 15:15)")
        
        # Align to full grid
        resampled = resampled.reindex(full_idx)
        resampled.index.name = 'timestamp'
        
        print(f"  After reindex: {len(resampled)} rows")
        print(f"  NaN count before fill: {resampled['close'].isna().sum()}")
        
        # Forward/backward fill close, then use close for O/H/L when missing; volume=0 for gaps
        resampled['close'] = resampled['close'].ffill().bfill()
        for col in ['open', 'high', 'low']:
            resampled[col] = resampled[col].fillna(resampled['close'])
        resampled['volume'] = resampled['volume'].fillna(0)
        
        print(f"  NaN count after fill: {resampled['close'].isna().sum()}")
        print(f"  Final time range: {resampled.index.min()} to {resampled.index.max()}")
        
        resampled['symbol'] = symbol
        resampled.reset_index(inplace=True)
        df_list.append(resampled)

df = pd.concat(df_list, ignore_index=True)
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n{'='*80}")
print(f"FINAL COMBINED DATA:")
print(f"{'='*80}")
print(f"Total rows: {len(df)}")
print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Symbols: {df['symbol'].unique()}")
print(f"Expected ticks (at 10 per candle): {len(df) * 10}")
print(f"\nFirst 5 rows:")
print(df.head())
print(f"\nLast 5 rows:")
print(df.tail())
print(f"\n{'='*80}\n")
