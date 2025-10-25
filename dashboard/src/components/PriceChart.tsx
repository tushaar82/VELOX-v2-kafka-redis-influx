/**
 * Price Chart - Real-time price with trailing SL overlay
 */
import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { api } from '../services/api';
import type { Position } from '../services/websocket';

interface PriceChartProps {
  symbol: string;
  position?: Position;
}

interface ChartDataPoint {
  timestamp: string;
  time: string;
  price: number;
  trailing_sl?: number;
  entry_price?: number;
}

export const PriceChart: React.FC<PriceChartProps> = ({ symbol, position }) => {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPriceData = async () => {
      try {
        setLoading(true);
        const response = await api.getPriceHistory(symbol, 1);

        const data: ChartDataPoint[] = response.prices.map((p: any) => ({
          timestamp: p.timestamp,
          time: new Date(p.timestamp).toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
          }),
          price: p.price,
          entry_price: position?.entry_price,
          trailing_sl: position?.trailing_sl,
        }));

        setChartData(data);
      } catch (error) {
        console.error('Error fetching price data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPriceData();

    // Refresh every 5 seconds
    const interval = setInterval(fetchPriceData, 5000);

    return () => clearInterval(interval);
  }, [symbol, position]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-80">
        <div className="text-dark-500">Loading chart...</div>
      </div>
    );
  }

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-80">
        <div className="text-dark-500">No price data available</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <div className="mb-4">
        <h3 className="text-lg font-bold text-dark-800">{symbol} - Price vs Trailing SL</h3>
        <p className="text-sm text-dark-500">Real-time price monitoring</p>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="time"
            stroke="#64748b"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="#64748b"
            style={{ fontSize: '12px' }}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '12px',
            }}
            formatter={(value: any) => `₹${Number(value).toFixed(2)}`}
          />
          <Legend />

          {/* Current Price Line */}
          <Line
            type="monotone"
            dataKey="price"
            stroke="#0ea5e9"
            strokeWidth={2}
            dot={false}
            name="Current Price"
            animationDuration={300}
          />

          {/* Entry Price Reference */}
          {position && (
            <ReferenceLine
              y={position.entry_price}
              stroke="#94a3b8"
              strokeDasharray="5 5"
              label={{ value: 'Entry', position: 'right', fill: '#64748b' }}
            />
          )}

          {/* Trailing SL Line */}
          {position?.trailing_sl && (
            <Line
              type="monotone"
              dataKey="trailing_sl"
              stroke="#ef4444"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Trailing SL"
            />
          )}

          {/* Highest Price Reference */}
          {position && (
            <ReferenceLine
              y={position.highest_price}
              stroke="#22c55e"
              strokeDasharray="3 3"
              label={{ value: 'High', position: 'right', fill: '#16a34a' }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Legend Info */}
      {position && (
        <div className="mt-4 grid grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-dark-500">Entry Price</p>
            <p className="font-semibold text-dark-800">₹{position.entry_price.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-dark-500">Current Price</p>
            <p className="font-semibold text-primary-600">₹{position.current_price.toFixed(2)}</p>
          </div>
          {position.trailing_sl && (
            <div>
              <p className="text-dark-500">Trailing SL</p>
              <p className="font-semibold text-danger-600">₹{position.trailing_sl.toFixed(2)}</p>
            </div>
          )}
          <div>
            <p className="text-dark-500">Highest Price</p>
            <p className="font-semibold text-success-600">₹{position.highest_price.toFixed(2)}</p>
          </div>
        </div>
      )}
    </div>
  );
};
