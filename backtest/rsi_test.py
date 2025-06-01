from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas as pd
import os
import warnings
import sys

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategy.rsi_strategy import rsi_combo, calculate_rsi, calculate_sma


def data_process(**kwargs) -> pd.DataFrame:
    df = pd.read_csv('tracked_data/nifty_data.csv')
    # processed_df = rsi_combo(df)
    processed_df = df.copy()

    if isinstance(processed_df, pd.DataFrame):
        print("✅ processed_df is a DataFrame")

    processed_df1 = processed_df.rename(columns={
        'close': 'Close',
        'datetime': 'Date',
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'volume': 'Volume',
        # 'RSI': 'RSI',
        # 'RSI_SMA': 'RSI_SMA'
    })

    processed_df1['Date'] = pd.to_datetime(processed_df1['Date'])

    # Only drop columns that exist
    remove_cols = kwargs.get('remove_columns')
    if remove_cols:
        if isinstance(remove_cols, str):
            remove_cols = [remove_cols]
        existing_cols = [col for col in remove_cols if col in processed_df1.columns]
        processed_df1 = processed_df1.drop(existing_cols, axis=1)

    if 'Date' in processed_df1.columns:
        processed_df1 = processed_df1.set_index('Date')
    else:
        print("❌ Error: 'Date' column not found after renaming for index setting.")

    # Filter for trading hours
    processed_df1 = processed_df1.between_time("09:15", "16:50")

    processed_df1 = processed_df1.dropna()
    processed_df1 = processed_df1.sort_index()

    return processed_df1


class SmaCross(Strategy):
    n1 = 14
    n2 = 14
    def init(self):
        close = self.data.Close
        self.rsi = self.I(calculate_rsi, close, self.n1, name='RSI')
        self.rsi_sma = self.I(calculate_sma, self.rsi, self.n2, name='RSI_SMA')

        

    def next(self):
        if not self.position:
            if crossover(self.rsi, self.rsi_sma):
                self.buy()
            elif crossover(self.rsi_sma, self.rsi):
                self.sell()
        else:
            # Close long and go short
            if self.position.is_long and crossover(self.rsi_sma, self.rsi):
                self.position.close()
                self.sell()
            # Close short and go long
            elif self.position.is_short and crossover(self.rsi, self.rsi_sma):
                self.position.close()
                self.buy()



# Run script
if __name__ == "__main__":
    print(f"📂 Working Dir: {os.getcwd()}")
    main_data = data_process(remove_columns='Volume')
    print(main_data.head())
    # one last year of data
    main_data = main_data.iloc[-(365 * 5):]

    bt = Backtest(main_data, SmaCross,
                  commission=.002,
                  exclusive_orders=True,
                  cash=100_000)

    stats = bt.run()
    print(stats)
    bt.plot(
    plot_volume=False,
    superimpose=True,  # This helps keep related indicators together
    open_browser=True
)
    # stats, heatmap = bt.optimize(
    #     n1=range(10, 110, 10),
    #     n2=range(20, 210, 20),
    #     n_enter=range(15, 35, 5),
    #     n_exit=range(10, 25, 5),
    #     # constraint=lambda p: p.n_exit < p.n_enter < p.n1 < p.n2,
    #     maximize='Equity Final [$]',
    #     max_tries=200,
    #     random_state=0,
    #     return_heatmap=True)
    # print(stats)
    # print(heatmap)

