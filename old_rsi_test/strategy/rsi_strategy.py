import pandas as pd


def calculate_rsi(data, periods):
    try:
        # Calculate price differences
        # check data a dataframe
        if isinstance(data, pd.DataFrame):
            data = data['Close']
        elif isinstance(data, pd.Series):
            data = data
        # if data is array
        else:
            data = pd.Series(data)
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
        
        # Calculate RS and RSI_SMA_SMA_SMA_SMA
        rs = avg_gain / avg_loss
        rsi = round(100 - (100 / (1 + rs)), 2)
    except Exception as e:
        print(f"Error calculating RSI: {e}")
        return None
    else:
     return rsi


def calculate_sma(data, window: int = 14) -> pd.Series:
    """Calculate the Simple Moving Average (SMA) for a given data series. limit 2 decimals"""
    # if data is array
    if isinstance(data, pd.Series):
        data = data
    else:
        data = pd.Series(data)
    return round(data.rolling(window=window).mean(), 3)


def rsi_combo(data, freq='1h'):
    """Calculate RSI and RSI SMA for a given DataFrame and time frequency."""
    # Ensure 'datetime' column is in datetime format
    data['datetime'] = pd.to_datetime(data['datetime'])
    # remove data before 09:15:00 of any day
    # Remove data before 09:15:00 of any day
    data = data[data['datetime'].dt.time >= pd.to_datetime('09:15:00').time()]
    # Group by frequency and get the last 'close' value for each period
    close = (
        data.groupby(pd.Grouper(key='datetime', origin='09:15:00', freq=freq))
        .agg({'close': 'last', 'datetime': 'last', 'open': 'first', 'high': 'max', 'low': 'min'})
        .dropna()
    )

    # Calculate RSI
    close['RSI'] = calculate_rsi(data=close['close'], periods=14)

    # Calculate RSI SMA
    close['RSI_SMA'] = calculate_sma(data=close['RSI'])

    return close
