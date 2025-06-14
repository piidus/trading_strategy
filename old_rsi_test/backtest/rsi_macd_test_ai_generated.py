import backtrader as bt
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# --- Configuration Parameters ---
SCRIPS = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']
START_DATE = '2020-01-01'
END_DATE = '2024-12-31'

OUTPUT_CSV_FILE = 'backtrader_backtest_summary_rsi_sma_revised.csv'
TRADE_DETAILS_CSV_FILE = 'backtrader_trade_details_rsi_sma_revised.csv'
PLOT_OUTPUT_DIR = 'temp_data/plots/'

SMA_SHORT_PERIOD = 50
SMA_LONG_PERIOD = 200

RSI_PERIOD = 14
RSI_MA_PERIOD = 21

INITIAL_CAPITAL = 100000
COMMISSION_PER_TRADE = 0.001


# --- Custom Data Feed Class for yfinance data ---
class PandasData(bt.feeds.PandasData):
    params = (
        ('datetime', None),
        ('open', -1),
        ('high', -1),
        ('low', -1),
        ('close', -1),
        ('volume', -1),
        ('openinterest', -1),
    )


# --- The Dual SMA-RSI Crossover Strategy ---
class DualSMARSIStrategy(bt.Strategy):
    params = (
        ('sma_short', SMA_SHORT_PERIOD),
        ('sma_long', SMA_LONG_PERIOD),
        ('rsi_period', RSI_PERIOD),
        ('rsi_ma_period', RSI_MA_PERIOD),
        ('commission_pct', COMMISSION_PER_TRADE),
        ('print_log', True),
        ('debug_next', True),
        ('starting_cash', INITIAL_CAPITAL)
    )

    def log(self, txt, dt=None):
        ''' Logging function for the strategy '''
        if self.p.print_log:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))


    def __init__(self):
        self.dataclose = self.datas[0].close
        self.data_name = self.datas[0]._name

        self.order = None
        self.trade_log = [] # List to store detailed trade information

        # SMA Indicators
        self.sma_s = bt.indicators.SMA(self.dataclose, period=self.p.sma_short)
        self.sma_l = bt.indicators.SMA(self.dataclose, period=self.p.sma_long)
        self.sma_cross = bt.indicators.CrossOver(self.sma_s, self.sma_l)

        # RSI and RSI-MA Indicators
        self.rsi = bt.indicators.RSI(self.dataclose, period=self.p.rsi_period)
        self.rsi_ma = bt.indicators.SMA(self.rsi, period=self.p.rsi_ma_period) # MA of RSI
        self.rsi_cross = bt.indicators.CrossOver(self.rsi, self.rsi_ma)
        

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            # Capture the transaction details at order completion
            transaction_details = {
                'Symbol': self.data_name,
                'Date': self.datas[0].datetime.date(0),
                'Price': order.executed.price,
                'Shares': order.executed.size,
                'Commission': order.executed.comm,
                'Entry_Date': self.datas[0].datetime.date(0), # Will be updated for exits
                'Exit_Date': None,
                'Exit_Price': None,
                'P&L': 0, # To be filled by notify_trade or exit logic
                'Net_P&L': 0, # To be filled by notify_trade or exit logic
                'Trade_Ref': order.ref # Use order reference to link to trades if needed
            }

            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))
                # If we're entering a long position
                if self.position.size > 0: # Checks if it's a new long position
                    transaction_details['Action'] = 'BUY (Long Entry)'
                    self.trade_log.append(transaction_details)
                else: # This was a buy to cover a short position
                    self.log(f'BUY EXECUTED (Short Exit), Price: {order.executed.price:.2f}, Shares: {order.executed.size}')
                    # The P&L for this will be handled in notify_trade when the overall short trade is closed
                    # No need to add a new entry here, the corresponding short entry will be updated.

            elif order.issell():
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                # If we're entering a short position
                if self.position.size < 0: # Checks if it's a new short position
                    transaction_details['Action'] = 'SELL (Short Entry)'
                    transaction_details['Shares'] = abs(order.executed.size) # Store positive shares for short
                    self.trade_log.append(transaction_details)
                else: # This was a sell to close a long position
                    self.log(f'SELL EXECUTED (Long Exit), Price: {order.executed.price:.2f}, Shares: {order.executed.size}')
                    # Update the corresponding long entry in trade_log
                    entry_trade_idx = -1
                    for i, trade_entry in reversed(list(enumerate(self.trade_log))):
                        if trade_entry['Symbol'] == self.data_name and trade_entry['Exit_Date'] is None and trade_entry['Action'] == 'BUY (Long Entry)':
                            entry_trade_idx = i
                            break
                    if entry_trade_idx != -1:
                        entry_price = self.trade_log[entry_trade_idx]['Price']
                        shares = self.trade_log[entry_trade_idx]['Shares']
                        entry_comm = self.trade_log[entry_trade_idx]['Commission']
                        gross_pl = (order.executed.price - entry_price) * shares
                        net_pl = gross_pl - entry_comm - order.executed.comm

                        self.trade_log[entry_trade_idx]['Action'] = 'SELL (Long Exit)'
                        self.trade_log[entry_trade_idx]['Exit_Date'] = self.datas[0].datetime.date(0)
                        self.trade_log[entry_trade_idx]['Exit_Price'] = order.executed.price
                        self.trade_log[entry_trade_idx]['P&L'] = gross_pl
                        self.trade_log[entry_trade_idx]['Net_P&L'] = net_pl
                        self.log(f'LONG EXIT P&L: Gross {gross_pl:.2f}, Net {net_pl:.2f}')
                    else:
                        self.log(f'ERROR: No matching BUY entry found for SELL order for {self.data_name}')

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        # This method is called when a trade is opened or closed.
        # We are primarily interested in closed trades for P&L.
        if not trade.isclosed:
            return

        self.log(f'OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')

        # Find the corresponding entry in trade_log and update it
        # This will cover both long and short trade closures
        entry_trade_idx = -1
        # Search for the *most recent* open trade (either long or short entry) for this symbol
        # that has not yet been exited.
        for i, log_entry in reversed(list(enumerate(self.trade_log))):
            if log_entry['Symbol'] == self.data_name and log_entry['Exit_Date'] is None:
                entry_trade_idx = i
                break

        if entry_trade_idx != -1:
            # Determine if it was a short trade that just closed (Action was 'SELL (Short Entry)')
            if 'Short Entry' in self.trade_log[entry_trade_idx]['Action']:
                self.trade_log[entry_trade_idx]['Action'] = 'BUY (Short Exit)' # Short exit is a buy
            # For long trades, notify_order already handled the exit action.
            # Here, we ensure P&L is updated from the trade object.
            self.trade_log[entry_trade_idx]['Exit_Date'] = self.datas[0].datetime.date(0)
            self.trade_log[entry_trade_idx]['Exit_Price'] = trade.price # The price at which the trade closed
            self.trade_log[entry_trade_idx]['P&L'] = trade.pnl
            self.trade_log[entry_trade_idx]['Net_P&L'] = trade.pnlcomm
        else:
            self.log(f'WARNING: notify_trade found closed trade ({trade.pnlcomm:.2f}) but no matching open entry in trade_log for {self.data_name}.')


    def next(self):
        if self.order:
            return

        current_date = self.datas[0].datetime.date(0)
        current_close = self.dataclose[0]
        current_pos_size = self.position.size

        required_bars_for_rsi_ma = self.p.rsi_period + self.p.rsi_ma_period - 1
        required_bars = max(self.p.sma_long, required_bars_for_rsi_ma) + 1

        if len(self) < required_bars:
            if self.p.debug_next:
                self.log(f"DEBUG: Insufficient bars ({len(self)}) for indicators (need at least {required_bars}). Skipping trade logic.")
            return

        if (self.sma_s[0] is None or pd.isna(self.sma_s[0]) or
            self.sma_l[0] is None or pd.isna(self.sma_l[0]) or
            self.rsi[0] is None or pd.isna(self.rsi[0]) or
            self.rsi_ma[0] is None or pd.isna(self.rsi_ma[0])):
            if self.p.debug_next:
                self.log(f"DEBUG: Indicators not ready/NaN. SMA_S={self.sma_s[0]:.2f}, SMA_L={self.sma_l[0]:.2f}, RSI={self.rsi[0]:.2f}, RSI_MA={self.rsi_ma[0]:.2f}. Skipping trade logic.")
            return

        sma_crossover_val = self.sma_cross[0]
        rsi_crossover_val = self.rsi_cross[0]

        if self.p.debug_next:
            self.log(f"DEBUG: Close={current_close:.2f}, Pos={current_pos_size}")
            self.log(f"DEBUG: SMA_S={self.sma_s[0]:.2f}, SMA_L={self.sma_l[0]:.2f}, SMA_Cross={sma_crossover_val}")
            self.log(f"DEBUG: RSI={self.rsi[0]:.2f}, RSI_MA={self.rsi_ma[0]:.2f}, RSI_Cross={rsi_crossover_val}")
            self.log(f"DEBUG: SMA_S > SMA_L: {self.sma_s[0] > self.sma_l[0]}, RSI > RSI_MA: {self.rsi[0] > self.rsi_ma[0]}")


        # --- Strategy Logic ---
        # Long Entry: SMA Short crosses above SMA Long AND RSI is currently above RSI MA
        long_entry_condition = (sma_crossover_val > 0) and (self.rsi[0] > self.rsi_ma[0])

        # Short Entry: SMA Short crosses below SMA Long AND RSI is currently below RSI MA
        short_entry_condition = (sma_crossover_val < 0) and (self.rsi[0] < self.rsi_ma[0])

        # Exit conditions remain the same (OR logic)
        long_exit_condition = (sma_crossover_val < 0) or (rsi_crossover_val < 0)
        short_exit_condition = (sma_crossover_val > 0) or (rsi_crossover_val > 0)

        if self.p.debug_next:
            self.log(f"DEBUG: Long Entry C={long_entry_condition}, Short Entry C={short_entry_condition}")
            self.log(f"DEBUG: Long Exit C={long_exit_condition}, Short Exit C={short_exit_condition}")


        # --- Trade Execution ---
        if current_pos_size == 0:
            if long_entry_condition:
                size = self.broker.getcash() // current_close
                if size > 0:
                    self.order = self.buy(size=size)
                    self.log(f'LONG ENTRY - SMA cross up & RSI aligned. Order size: {size}')
            elif short_entry_condition:
                size = self.broker.getcash() // current_close
                if size > 0:
                    self.order = self.sell(size=size)
                    self.log(f'SHORT ENTRY - SMA cross down & RSI aligned. Order size: {size}')

        elif current_pos_size > 0: # Currently IN LONG POSITION
            if long_exit_condition:
                self.order = self.close()
                self.log('LONG EXIT - SMA OR RSI cross down.')
            elif short_entry_condition: # Opportunity to reverse
                self.order = self.close()
                self.log('LONG POSITION CLOSED - Reversing to SHORT.')
                size = self.broker.getcash() // current_close
                if size > 0:
                    self.order = self.sell(size=size)
                    self.log(f'SHORT ENTRY AFTER REVERSE - Order size: {size}')

        elif current_pos_size < 0: # Currently IN SHORT POSITION
            if short_exit_condition:
                self.order = self.close()
                self.log('SHORT EXIT - SMA OR RSI cross up.')
            elif long_entry_condition: # Opportunity to reverse
                self.order = self.close()
                self.log('SHORT POSITION CLOSED - Reversing to LONG.')
                size = self.broker.getcash() // current_close
                if size > 0:
                    self.order = self.buy(size=size)
                    self.log(f'LONG ENTRY AFTER REVERSE - Order size: {size}')


    def stop(self):
        final_value = self.broker.getvalue()
        total_return = (final_value - self.p.starting_cash) / self.p.starting_cash

        num_trading_days = len(self.datas[0])
        annualized_return_calc = 0
        if num_trading_days > 0:
            first_date = self.datas[0].datetime.date(0)
            last_date = self.datas[0].datetime.date(-1)
            delta_days = (last_date - first_date).days
            years_in_backtest = delta_days / 365.25
            if years_in_backtest <= 0: years_in_backtest = 1/252
            annualized_return_calc = (1 + total_return)**(1 / years_in_backtest) - 1

        return {
            'symbol': self.data_name,
            'initial_capital': self.p.starting_cash,
            'final_capital': final_value,
            'total_return': total_return,
            'annualized_return_calculated': annualized_return_calc,
            'num_trades': len([t for t in self.trade_log if 'Entry' in t['Action']]),
            'trade_log': self.trade_log
        }


# --- Main Backtesting Execution ---
if __name__ == '__main__':
    os.makedirs(PLOT_OUTPUT_DIR, exist_ok=True)

    all_backtest_summary = []
    all_detailed_trades = []

    for scrip_symbol in SCRIPS:
        print(f"\n--- Running Backtest for {scrip_symbol} ---")

        # 1. Fetch Data
        df = yf.download(scrip_symbol, start=START_DATE, end=END_DATE, auto_adjust=True)
        if df.empty:
            print(f"Skipping {scrip_symbol}: No data found for the specified period.")
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower().replace(' ', '_') for col in df.columns]
        else:
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]

        data = PandasData(dataname=df, name=scrip_symbol)
        print(data)

        # 2. Initialize Cerebro
        cerebro = bt.Cerebro()
        cerebro.adddata(data)

        # 3. Add Strategy
        cerebro.addstrategy(DualSMARSIStrategy, starting_cash=INITIAL_CAPITAL, debug_next=True)

        # 4. Set Initial Capital and Commission
        cerebro.broker.setcash(INITIAL_CAPITAL)
        cerebro.broker.setcommission(commission=COMMISSION_PER_TRADE)

        # 5. Add Analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

        # 6. Run the Backtest
        print("Running backtest...")
        strategies = cerebro.run()
        thestrat = strategies[0]

        # 7. Collect Results
        strategy_summary = thestrat.stop()

        sharpe_ratio = thestrat.analyzers.sharpe.get_analysis().get('sharperatio', None)
        max_drawdown = thestrat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', None)
        total_return_analyzer = thestrat.analyzers.returns.get_analysis().get('rtot', None)
        annual_return_analyzer_pct = thestrat.analyzers.returns.get_analysis().get('rnorm100', None)

        strategy_summary['sharpe_ratio'] = sharpe_ratio
        strategy_summary['max_drawdown'] = max_drawdown
        strategy_summary['total_return_analyzer'] = total_return_analyzer
        strategy_summary['annualized_return_analyzer'] = annual_return_analyzer_pct / 100 if annual_return_analyzer_pct is not None else None

        all_backtest_summary.append(strategy_summary)
        all_detailed_trades.extend(strategy_summary.pop('trade_log'))

        # 8. Plotting
        print(f"Generating plot for {scrip_symbol}...")
        try:
            cerebro.plot(style='candlestick',
                         plotname=f'{scrip_symbol} Dual SMA-RSI Crossover Backtest',
                         path=PLOT_OUTPUT_DIR,
                         filename=f'{scrip_symbol}_dual_sma_rsi_crossover_backtest.html',
                         fmt='html',
                         iplot=False)
            print(f"Plot saved for {scrip_symbol} in {os.path.join(PLOT_OUTPUT_DIR, f'{scrip_symbol}_dual_sma_rsi_crossover_backtest.html')}")
        except Exception as e:
            print(f"Warning: Could not generate plot for {scrip_symbol}. Error: {e}")


    # --- Final Output: Save Results to CSV ---
    results_df = pd.DataFrame(all_backtest_summary)
    results_df.set_index('symbol', inplace=True)
    results_df.sort_values(by='total_return_analyzer', ascending=False, inplace=True)

    detailed_trades_df = pd.DataFrame(all_detailed_trades)
    if not detailed_trades_df.empty:
        detailed_trades_df['Date'] = pd.to_datetime(detailed_trades_df['Date'])
        if 'Entry_Date' in detailed_trades_df.columns:
            detailed_trades_df['Entry_Date'] = pd.to_datetime(detailed_trades_df['Entry_Date'])
        if 'Exit_Date' in detailed_trades_df.columns:
            detailed_trades_df['Exit_Date'] = pd.to_datetime(detailed_trades_df['Exit_Date'])
        detailed_trades_df.sort_values(by=['Symbol', 'Date'], inplace=True)

    results_df.to_csv(OUTPUT_CSV_FILE)
    detailed_trades_df.to_csv(TRADE_DETAILS_CSV_FILE, index=False)

    print(f"\n--- Backtesting Complete ---")
    print(f"Summary results saved to: {OUTPUT_CSV_FILE}")
    print(f"Detailed trade logs saved to: {TRADE_DETAILS_CSV_FILE}")
    print(f"Interactive plots saved in: {PLOT_OUTPUT_DIR}")

    print("\n--- Overall Backtest Summary ---")
    print(results_df)