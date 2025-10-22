"""
Data quality validator for market data.
Checks for gaps, anomalies, and data integrity issues.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from .logging_config import get_logger


class DataValidator:
    """Validates market data quality and generates reports."""
    
    def __init__(self):
        """Initialize data validator."""
        self.logger = get_logger('data_validator')
        self.validation_results = []
    
    def validate_day(self, df: pd.DataFrame, date: str, expected_minutes: int = 375) -> Dict:
        """
        Validate data for a single trading day.
        
        Args:
            df: DataFrame with intraday data
            date: Date string
            expected_minutes: Expected number of minutes (9:15-3:30 = 375)
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'date': date,
            'symbols': df['symbol'].unique().tolist() if 'symbol' in df.columns else [],
            'total_rows': len(df),
            'issues': []
        }
        
        if df.empty:
            results['issues'].append("No data available")
            return results
        
        # Check for each symbol
        for symbol in results['symbols']:
            symbol_df = df[df['symbol'] == symbol].copy()
            symbol_results = self._validate_symbol_day(symbol_df, symbol, date, expected_minutes)
            
            if symbol_results['issues']:
                results['issues'].extend([f"{symbol}: {issue}" for issue in symbol_results['issues']])
        
        # Log results
        if results['issues']:
            self.logger.warning(f"Validation issues for {date}: {len(results['issues'])} problems found")
            for issue in results['issues'][:5]:  # Log first 5
                self.logger.warning(f"  - {issue}")
        else:
            self.logger.info(f"Validation passed for {date}: {results['total_rows']} rows")
        
        self.validation_results.append(results)
        return results
    
    def _validate_symbol_day(self, df: pd.DataFrame, symbol: str, date: str, 
                            expected_minutes: int) -> Dict:
        """Validate data for a single symbol on a single day."""
        results = {
            'symbol': symbol,
            'date': date,
            'row_count': len(df),
            'issues': []
        }
        
        # Check row count
        if len(df) < expected_minutes * 0.9:  # Allow 10% tolerance
            results['issues'].append(
                f"Low row count: {len(df)} (expected ~{expected_minutes})"
            )
        
        # Check for timestamp gaps
        if len(df) > 1:
            df = df.sort_values('timestamp')
            df['time_diff'] = df['timestamp'].diff()
            
            # Gaps larger than 2 minutes (allowing for some flexibility)
            large_gaps = df['time_diff'] > timedelta(minutes=2)
            if large_gaps.any():
                gap_count = large_gaps.sum()
                results['issues'].append(f"Found {gap_count} timestamp gaps > 2 minutes")
        
        # Validate OHLC relationships
        invalid_high = df['high'] < df[['open', 'low', 'close']].max(axis=1)
        if invalid_high.any():
            results['issues'].append(f"{invalid_high.sum()} rows with high < max(O,L,C)")
        
        invalid_low = df['low'] > df[['open', 'high', 'close']].min(axis=1)
        if invalid_low.any():
            results['issues'].append(f"{invalid_low.sum()} rows with low > min(O,H,C)")
        
        # Check for zero or negative prices
        zero_prices = (df[['open', 'high', 'low', 'close']] <= 0).any(axis=1)
        if zero_prices.any():
            results['issues'].append(f"{zero_prices.sum()} rows with zero/negative prices")
        
        # Check for extreme price changes (>5% in 1 minute)
        if len(df) > 1:
            df['price_change_pct'] = df['close'].pct_change().abs() * 100
            extreme_changes = df['price_change_pct'] > 5.0
            if extreme_changes.any():
                results['issues'].append(
                    f"{extreme_changes.sum()} extreme price jumps (>5% in 1 min)"
                )
        
        # Check for zero volume
        zero_volume = df['volume'] == 0
        if zero_volume.any():
            zero_pct = (zero_volume.sum() / len(df)) * 100
            if zero_pct > 10:  # More than 10% zero volume is suspicious
                results['issues'].append(f"{zero_pct:.1f}% rows with zero volume")
        
        return results
    
    def generate_report(self, output_file: str = 'reports/data_quality_report.txt'):
        """
        Generate a comprehensive data quality report.
        
        Args:
            output_file: Path to output report file
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("VELOX DATA QUALITY REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Summary statistics
            total_days = len(self.validation_results)
            days_with_issues = sum(1 for r in self.validation_results if r['issues'])
            total_issues = sum(len(r['issues']) for r in self.validation_results)
            
            f.write(f"Total days validated: {total_days}\n")
            f.write(f"Days with issues: {days_with_issues}\n")
            f.write(f"Total issues found: {total_issues}\n")
            f.write(f"Data quality score: {((total_days - days_with_issues) / total_days * 100):.1f}%\n")
            f.write("\n" + "-" * 80 + "\n\n")
            
            # Detailed results
            f.write("DETAILED VALIDATION RESULTS\n\n")
            
            for result in self.validation_results:
                f.write(f"Date: {result['date']}\n")
                f.write(f"Symbols: {', '.join(result['symbols'])}\n")
                f.write(f"Total rows: {result['total_rows']}\n")
                
                if result['issues']:
                    f.write(f"Issues found: {len(result['issues'])}\n")
                    for issue in result['issues']:
                        f.write(f"  - {issue}\n")
                else:
                    f.write("Status: ✓ PASSED\n")
                
                f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("END OF REPORT\n")
        
        self.logger.info(f"Data quality report saved to {output_path}")
        print(f"\nData quality report saved to {output_path}")
    
    def get_summary(self) -> Dict:
        """Get summary statistics of validation results."""
        if not self.validation_results:
            return {}
        
        total_days = len(self.validation_results)
        days_with_issues = sum(1 for r in self.validation_results if r['issues'])
        total_issues = sum(len(r['issues']) for r in self.validation_results)
        
        return {
            'total_days': total_days,
            'days_with_issues': days_with_issues,
            'total_issues': total_issues,
            'quality_score': ((total_days - days_with_issues) / total_days * 100) if total_days > 0 else 0
        }


if __name__ == "__main__":
    # Test validator
    from ..adapters.data.historical import HistoricalDataManager
    from .logging_config import initialize_logging
    import logging
    
    initialize_logging(log_level=logging.INFO)
    
    # Load some data
    hdm = HistoricalDataManager('./data')
    stats = hdm.get_statistics()
    
    if stats['symbols']:
        validator = DataValidator()
        
        # Validate a few random dates
        symbol = stats['symbols'][0]
        dates = hdm.get_available_dates(symbol)
        
        # Test 5 random dates
        import random
        test_dates = random.sample(dates, min(5, len(dates)))
        
        print(f"\nValidating {len(test_dates)} random dates for {symbol}...")
        
        for date in test_dates:
            df = hdm.get_data(date, [symbol])
            validator.validate_day(df, date)
        
        # Generate report
        validator.generate_report()
        
        # Print summary
        summary = validator.get_summary()
        print(f"\n=== Validation Summary ===")
        print(f"Total days: {summary['total_days']}")
        print(f"Days with issues: {summary['days_with_issues']}")
        print(f"Quality score: {summary['quality_score']:.1f}%")
