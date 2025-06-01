from backtesting import Backtest, Strategy
from backtesting.lib import crossover, plot_heatmaps
import pandas as pd
import numpy as np
import os
import warnings
import sys

warnings.filterwarnings("ignore")

class OptimizedRSICross(Strategy):
    # Optimizable parameters
    rsi_period = 14
    sma_period = 14
    overbought = 70
    oversold = 30
    take_profit_pct = 0.03  # 3%
    stop_loss_pct = 0.015    # 1.5%
    
    def init(self):
        close = self.data.Close
        # Calculate indicators
        self.rsi = self.I(self.calculate_rsi, close, self.rsi_period, name='RSI')
        self.rsi_sma = self.I(self.calculate_sma, self.rsi, self.sma_period, name='RSI_SMA')
        
        # For position management
        self.take_profit_level = None
        self.stop_loss_level = None
    
    @staticmethod
    def calculate_rsi(series, period):
        if isinstance(series, pd.Series):
            series = series
        else:
            series = pd.Series(series)
        delta = series.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_sma(series, period):
        if isinstance(series, pd.Series):
            series = series
        else:
            series = pd.Series(series)
        return series.rolling(period).mean()
    
    def next(self):
        price = self.data.Close[-1]
        
        # Close positions if TP/SL hit
        if self.position:
            if self.position.is_long:
                if price >= self.take_profit_level or price <= self.stop_loss_level:
                    self.position.close()
            elif self.position.is_short:
                if price <= self.take_profit_level or price >= self.stop_loss_level:
                    self.position.close()
            return
        
        # Entry conditions
        rsi_val = self.rsi[-1]
        
        # Long entry: RSI crosses above SMA and coming from oversold
        if( crossover(self.rsi, self.rsi_sma) and (rsi_val < self.oversold + 10)):
            self.buy()
            self.take_profit_level = price * (1 + self.take_profit_pct)
            self.stop_loss_level = price * (1 - self.stop_loss_pct)
        
        # Short entry: RSI crosses below SMA and coming from overbought
        elif (crossover(self.rsi_sma, self.rsi) and (rsi_val > self.overbought - 10)):
            self.sell()
            self.take_profit_level = price * (1 - self.take_profit_pct)
            self.stop_loss_level = price * (1 + self.stop_loss_pct)

def data_process(filepath='tracked_data/nifty_data.csv', **kwargs):
    try:
        df = pd.read_csv(filepath)
        print(f"Data loaded successfully. Columns: {df.columns.tolist()}")
        
        df = df.rename(columns={
            'close': 'Close',
            'datetime': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'volume': 'Volume',
        })
        
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date')
        df = df.between_time("09:15", "16:50")
        
        print(f"Data sample after processing:\n{df.head()}")
        print(f"Data range: {df.index.min()} to {df.index.max()}")
        
        return df.dropna()
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        raise

if __name__ == "__main__":
    print("Starting backtest...")
    
    try:
        data = data_process()
        if data.empty:
            raise ValueError("Processed data is empty!")
            
        # data = data.iloc[-(365*3):]  # Last 3 years
        print(f"Final data shape: {data.shape}")
        
        bt = Backtest(data, OptimizedRSICross,
                     commission=.002,
                     exclusive_orders=True,
                     cash=100_000,
                     trade_on_close=True,
                     margin=1.0)
        
        # First run with default parameters
        print("\nRunning with default parameters...")
        default_stats = bt.run()
        print(default_stats)
        bt.plot(filename='default_backtest.html')
        
        # Then optimize
        print("\nOptimizing parameters...")
        stats, heatmap = bt.optimize(
            rsi_period=range(10, 21, 2),
            sma_period=range(10, 31, 5),
            overbought=range(65, 76, 5),
            oversold=range(25, 36, 5),
            take_profit_pct=[0.02, 0.03, 0.04],
            stop_loss_pct=[0.01, 0.015, 0.02],
            maximize='Return [%]',
            max_tries=50,  # Reduced for faster testing
            random_state=42,
            return_heatmap=True)
        
        print("\nOptimized Strategy Results:")
        print(stats)
        bt.plot(filename='optimized_backtest.html')
        
        # Plot optimization heatmap
        if heatmap is not None:
            plot_heatmaps(heatmap, agg='mean', plot_width=1000)
        else:
            print("No heatmap data available")
            
    except Exception as e:
        print(f"Error in backtest: {str(e)}")
        raise