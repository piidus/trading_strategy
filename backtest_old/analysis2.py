import pandas as pd
import openpyxl
import matplotlib.pyplot as plt
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

def data_preprocessing() -> pd.DataFrame:
    
    """
    This function takes the raw data from 'analysis_data/nifty_5year.csv',
    drops the 'Unnamed: 0' and 'volume' columns, sets the 'datetime' column as the index, and
    resamples the data to 1 hour intervals beginning at 09:15:00. It then drops any remaining
    NaN values and limits the data to between 09:15:00 and 16:15:00.

    Returns:
        pd.DataFrame: Processed data
    """

    main_data = pd.read_csv('analysis_data/nifty_5year.csv')
    # # drop
    main_data = main_data.drop(['Unnamed: 0', 'volume'], axis=1)
    main_data['datetime'] = pd.to_datetime(main_data['datetime'])
    # make  1hr data
    main_data = main_data.set_index('datetime')
    main_data = main_data.resample('1h', origin='09:15:00').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'})
    # drop na
    main_data = main_data.dropna()
    # takes only 9:15 to 16:15
    main_data = main_data.between_time('09:15:00', '16:15:00')
    return main_data

def calculate_rsi(data, periods):
    # Calculate price differences
    price_diff = data.diff()
    
    # Separate gains and losses
    gains = price_diff.where(price_diff > 0, 0)
    losses = -price_diff.where(price_diff < 0, 0)
    
    # Calculate sum of gains and losses
    sum_gains = gains.rolling(window=periods).sum()
    sum_losses = losses.rolling(window=periods).sum()
    
    # Calculate average gains and losses
    avg_gain = sum_gains / periods
    avg_loss = sum_losses / periods
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = round(100 - (100 / (1 + rs)), 2)
    return rsi

# Define a function to calculate SMA for a given window
def calculate_sma(window):
    return window.sum() / 14
# rsi and sma calc
def rsi_combo(df: pd.DataFrame) -> pd.DataFrame:
    rsi_df = df.copy()
    rsi_df['RSI'] = calculate_rsi(rsi_df['close'], periods=14)
    rsi_df['RSI_SMA'] = rsi_df['RSI'].rolling(window = 14).apply(calculate_sma, raw=True)
    # dropna
    rsi_df = rsi_df.dropna()
    return rsi_df

def generate_signals_with_crossover(df: pd.DataFrame) -> pd.DataFrame:
    df = df.reset_index()
    df['Signal'] = 'Waiting'  # Default state is 'Waiting'
    for i in range(1, len(df)):
        current_row = df.iloc[i]
        prev_row = df.iloc[i - 1]

        if (prev_row['RSI'] <= prev_row['RSI_SMA'] and current_row['RSI'] > current_row['RSI_SMA'] and prev_row['RSI_SMA'] < 35):
            df.at[i, 'Signal'] = 'Buy'
        elif (prev_row['RSI'] >= prev_row['RSI_SMA'] and current_row['RSI'] < current_row['RSI_SMA'] and prev_row['Signal'] != 'Waiting' and prev_row['RSI_SMA']> 65):
            df.at[i, 'Signal'] = 'Sell'
        elif (prev_row['Signal'] == 'Buy' or prev_row['Signal'] == 'Hold'):
            df.at[i, 'Signal'] = 'Hold'
        elif (prev_row['Signal'] == 'Sell' or prev_row['Signal'] == 'Waiting'):
            df.at[i, 'Signal'] = 'Waiting'
        else:
            df.at[i, 'Signal'] = 'UPDATE'
    return df


def raturn_calculator(nifty_data: pd.DataFrame, etf_data: pd.DataFrame) -> pd.DataFrame:
    transaction_data = pd.DataFrame()
    # filter only buy and sell
    transaction_data = nifty_data[(nifty_data['Signal'] == 'Buy') | (nifty_data['Signal'] == 'Sell')].reindex()
    # drop Unnamed: 0
    transaction_data = transaction_data.drop(['Unnamed: 0'], axis=1).reset_index(drop=True)

    # find same time values from etf_data
    transaction_data['datetime'] = pd.to_datetime(transaction_data['datetime'])
    etf_data['datetime'] = pd.to_datetime(etf_data['datetime'])
    # etf close rename as etf_close
    etf_data = etf_data.rename(columns={'close': 'etf_close'})
    
    etf_data = etf_data[['datetime', 'etf_close']]
    etf_data = etf_data.set_index('datetime')
    transaction_data = transaction_data.set_index('datetime')
    transaction_data = transaction_data.join(etf_data, how='left', on='datetime')

    # print(transaction_data)
    return transaction_data


def plot_data(data: pd.DataFrame) -> None:
    # plot nifty close with signal and below it 
    # 2nd plot rsi and rsi sma both and scrollable in plotly
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
    fig.add_trace(go.Scatter(x=data['datetime'], y=data['close'], mode='lines', name='Nifty Close'), row=1, col=1)
    fig.add_trace(go.Scatter(x=data['datetime'], y=data['RSI'], mode='lines', name='RSI'), row=2, col=1)
    fig.add_trace(go.Scatter(x=data['datetime'], y=data['RSI_SMA'], mode='lines', name='RSI_SMA'), row=2, col=1)
    fig.add_trace(go.Scatter(x=data['datetime'], y=data['Signal'], mode='markers', name='Signal'), row=1, col=1)
    fig.update_layout(title='Nifty Close with Signal and RSI', xaxis_title='Datetime', yaxis_title='Price')
    fig.show()
    

if __name__ == '__main__':
    # preprossed_data = data_preprocessing()
    # print(preprossed_data.head(30))
    # rsi_data = rsi_combo(preprossed_data)
    # print(rsi_data)
    # signals = generate_signals_with_crossover(rsi_data)
    # print(signals)
    # save to csv
    # signals.to_csv('analysis_data/analysis2_with_signal_with_crossover.csv')
    # raturn_calculator
    nifty_data = pd.read_csv('analysis_data/analysis2_with_signal_with_crossover.csv')
    etf_data = pd.read_csv('analysis_data/SBINIF_5year.csv')
    # final =raturn_calculator(nifty_data=nifty_data, etf_data=etf_data)
    # final.to_excel('analysis_data/analysis2_fineal.xlsx')
    # graph data
    plot_data(data = nifty_data)