
import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

const AdvancedPriceChart = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeframe, setTimeframe] = useState('1Y');
  const [selectedIndicators, setSelectedIndicators] = useState(['sma_50', 'rsi']);
  const [chartType, setChartType] = useState('candlestick');

  const fetchChartData = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `/api/v1/price-data/advanced-chart-data/?ticker=AAPL&timeframe=${timeframe}&indicators=${selectedIndicators.join(',')}`
      );

      if (!response.ok) throw new Error('Failed to fetch data');

      const result = await response.json();
      setData(result.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChartData();
  }, [timeframe, selectedIndicators]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-500 p-4">
        Error: {error}
      </div>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-2xl font-bold">Technical Analysis</CardTitle>
        <div className="flex gap-4">
          <Select value={timeframe} onValueChange={setTimeframe}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Timeframe" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1D">1 Day</SelectItem>
              <SelectItem value="1W">1 Week</SelectItem>
              <SelectItem value="1M">1 Month</SelectItem>
              <SelectItem value="3M">3 Months</SelectItem>
              <SelectItem value="6M">6 Months</SelectItem>
              <SelectItem value="1Y">1 Year</SelectItem>
              <SelectItem value="5Y">5 Years</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={chartType}
            onValueChange={setChartType}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Chart Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="candlestick">Candlestick</SelectItem>
              <SelectItem value="line">Line</SelectItem>
              <SelectItem value="area">Area</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>

      <CardContent>
        <div className="h-[600px] mt-4">
          <ResponsiveContainer width="100%" height="100%">
            {chartType === 'candlestick' ? (
              <CompositeChart data={data}>
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <CartesianGrid strokeDasharray="3 3" />
                {/* Candlestick custom renderer */}
                {data.map((entry, index) => (
                  <rect
                    key={`candle-${index}`}
                    x={index * (width / data.length)}
                    y={Math.min(entry.open_price, entry.close_price)}
                    width={Math.max(1, width / data.length - 1)}
                    height={Math.abs(entry.close_price - entry.open_price)}
                    fill={entry.close_price >= entry.open_price ? '#26a69a' : '#ef5350'}
                  />
                ))}
                {selectedIndicators.includes('sma_50') && (
                  <Line
                    type="monotone"
                    dataKey="sma_50"
                    stroke="#8884d8"
                    dot={false}
                    name="50 SMA"
                  />
                )}
                {selectedIndicators.includes('rsi') && (
                  <Line
                    type="monotone"
                    dataKey="rsi"
                    stroke="#82ca9d"
                    dot={false}
                    name="RSI"
                    yAxisId="right"
                  />
                )}
              </CompositeChart>
            ) : chartType === 'line' ? (
              <LineChart data={data}>
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <CartesianGrid strokeDasharray="3 3" />
                <Line
                  type="monotone"
                  dataKey="close_price"
                  stroke="#8884d8"
                  dot={false}
                  name="Price"
                />
              </LineChart>
            ) : (
              <AreaChart data={data}>
                <XAxis dataKey="date" />
                <YAxis />
                <CartesianGrid strokeDasharray="3 3" />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="close_price"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.3}
                  name="Price"
                />
              </AreaChart>
            )}
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

export default AdvancedPriceChart;