import pandas as pd
import os
import json

# get the data
def get_data() -> list:
    # read etf list to get file name
    """
    Read the etf_list.csv file to get the list of etf names in ShortName column, 
    convert it to a string with comma separated values and return it.

    Returns:
        list: a list of string with comma separated values of etf names
    """
    etf_list = pd.read_csv('MTF_PORTFOLIO/etf_list.csv')
    etf_list = etf_list['ShortName'].tolist()
    # etf_list = [str(i) for i in etf_list]
    # etf_list = ','.join(etf_list)
    # print(etf_list)
    return etf_list

# 20 days sma
def sma_20(df):
    df['20day_sma'] = df['close'].rolling(window=20).mean()
    return df

def check_and_adjust_splits(df):
    """
    Detects stock splits in the data, adjusts previous rows accordingly, 
    and rechecks for further splits.

    Args:
        df (pd.DataFrame): DataFrame containing stock data with a 'close' column.

    Returns:
        pd.DataFrame: Adjusted DataFrame after accounting for splits.
    """
    try:
        # Ensure DataFrame has enough rows to check splits
        if len(df) < 3:
            print("Insufficient data to check for splits.")
            return df

        # Perform split detection and adjustment
        split_detected = True
        while split_detected:
            split_detected = False
            for index, row in df.iloc[2:].iterrows():
                # Safely access previous and pre-previous rows
                previous_close = float(df.iloc[index - 1]['close'])
                pre_previous_close = float(df.iloc[index - 2]['close'])
                close = float(row['close'])

                # Detect a potential split
                if previous_close > close * 1.5 and pre_previous_close > close * 1.5:
                    # Calculate the split ratio
                    if previous_close > 0:
                        split_ratio = round(previous_close / close)
                        if split_ratio > 1:  # Ensure a meaningful split ratio
                            print(
                                f"Split detected at index {index}: "
                                f"Ratio={split_ratio}, stock_name={row.get('ShortName', 'N/A')}, "
                                f"PrePrevious={pre_previous_close}, Previous={previous_close}, Current={close}"
                            )
                            # Adjust all previous rows
                            df.loc[:index - 1, 'close'] /= split_ratio
                            split_detected = True
                            break  # Restart the loop after adjustment

    except Exception as e:
        print(f"[ERROR] Error during split detection and adjustment: {e}")

    return df

def remove_next_if_greater(df):
    """
    Removes rows where the *next* row's 'Close' value is more than 15% 
    greater than the *current* row's 'Close' value. Repeats until no more 
    rows need to be removed.

    Args:
        df (pd.DataFrame): DataFrame containing a 'Close' column.

    Returns:
        pd.DataFrame: Cleaned DataFrame.
    """
    if df.empty or 'close' not in df.columns:
        print("The DataFrame is empty or missing the 'Close' column.")
        return df

    while True:  # Loop until no more rows are removed
        percentage_change = df['close'].pct_change()
        indices_to_remove = percentage_change[percentage_change > 0.15].index

        if indices_to_remove.empty:
            break  # Exit loop if no rows need to be removed

        print(f"Indices of rows to remove: {indices_to_remove.tolist()}")
        df = df.drop(indices_to_remove).reset_index(drop=True)

    return df


def data_clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and processes a DataFrame by handling missing values, 
    detecting stock splits, adjusting historical data, and adding SMA and difference columns.

    Args:
        df (pd.DataFrame): Input DataFrame containing stock data with columns:
                           'open', 'high', 'low', 'volume', and 'close'.

    Returns:
        pd.DataFrame: Cleaned DataFrame with additional columns and adjusted data.
    """
    required_columns = ['open', 'high', 'low', 'volume', 'close']
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"Input DataFrame must contain the columns: {required_columns}")

    # Initial preprocessing
    df = df.dropna().reset_index(drop=True)
    df = df.drop(['open', 'high', 'low', 'volume'], axis=1)
    # check for splits in the data if any then adjust accordingly and recheck again
    try:
        df = check_and_adjust_splits(df)
        df = remove_next_if_greater(df)
        # Add SMA and calculate difference
        df['20day_sma'] = df['close'].rolling(window=20).mean()
        df['diff'] = df['close'] - df['20day_sma']
        df = df.dropna()

        

    except Exception as e:
        print(f"[ERROR in data_clean] {type(e).__name__}: {e}")

    return df

        # pass

def data_read(etf_list: str) -> pd.DataFrame:
    """
    Reads data from a CSV file and processes it using the `data_clean` function.

    Args:
        etf_list (str): A comma-separated string of ETF names.

    Returns:
        pd.DataFrame: A DataFrame containing the processed data from the CSV file.
    """
    mega_df = pd.DataFrame()
    for etf in etf_list:
        # print(etf)
        try:
            df = pd.read_csv(f'MTF_PORTFOLIO/data/{etf}.csv')
            df = data_clean(df)
            # print(df.head())
        except Exception as e:
            print('[ERROR in data_read]',etf,e)
        else:
            mega_df = pd.concat([mega_df, df], axis=0, ignore_index=True)
            # sort by date reverse
            mega_df = mega_df.sort_values(by='datetime', ascending=True)
            # mega_df = mega_df.sort_values(by='datetime')
    return mega_df


def portfolio_analysis(df: pd.DataFrame) -> pd.DataFrame:
    '''
    total portfolio value = 5,00,000
    per day investment = total portfolio value / 40
    max stock per day = 3
    step 1: get 5 years date
    step 2: for every day if date avialable find lowest diff and not in portfolio add it to portfolio for per day investment
    step 3: for every day check portfolio any stock cross 3% if true then remove from portfolio and 
        add to investment and calculate new portfolio and holding days and profit value

    '''
    portfolio_value = 5_00_000
    per_stock_investment = 12400
    max_stock_per_day = 3
    holding :pd.DataFrame = pd.DataFrame(columns=['date','stock','avg_price','ltp','signal','quantity', 'trans_no'])
    tranaction :pd.DataFrame = pd.DataFrame(columns=['date','stock','avg_price', 'ltp','signal','quantity','profit', 'days_holding', 'balance', 'trans_no'])
    # get 5 years date by unique
    trans_no = 0
    df['datetime'] = pd.to_datetime(df['datetime'])
    trading_dates = df['datetime'].unique()
    
    for date in trading_dates:
        # print(date)
        one_day_df = df[df['datetime'] == date]
        # print(df_date.head())
        temp_hold :int = max_stock_per_day
        for index, row in one_day_df.iterrows():
            # maintaining holding
            if row['ShortName'] in holding['stock'].tolist():
                stock_name = row['ShortName']
                stock_price = float(row['close'])
                old_price = float(holding[holding['stock'] == stock_name]['avg_price'].values[0])
                last_traded_price = float(holding[holding['stock'] == stock_name]['ltp'].values[0])
                old_quantity = int(holding[holding['stock'] == stock_name]['quantity'].values[0])
                

                # check if stock cross 3%
                if stock_price >= old_price * 1.03:
                    quantity = int(holding[holding['stock'] == stock_name]['quantity'].values[0])
                    print(f"{stock_name} cross 3%, [stock_price: {stock_price}, latest_price: {old_price}, quantity: {quantity}]")
                    # add to tranaction
                    # profit = (float(stock_price) - float(old_price)) * holding
                    profit = (stock_price - old_price) * (old_quantity * 3)
                    _trans_no = holding[holding['stock'] == stock_name]['trans_no'].values[0]

                    # maintaining balance
                    portfolio_value += (stock_price * old_quantity)
                    per_stock_investment += (profit / 40)
                    days_holding = (date - holding[holding['stock'] == stock_name]['date'].values[0]).days
                    data_for_adding ={'date':date, 'stock':stock_name, 'avg_price':stock_price, 'ltp':last_traded_price, 'signal':'sell', 'quantity':quantity, 'profit':profit, 'days_holding':days_holding, 'balance':portfolio_value, 'trans_no':_trans_no}
                    tranaction.loc[len(tranaction)] = data_for_adding
                    # remove from holding
                    holding = holding[holding['stock'] != stock_name]
                    print(f"{stock_name} cross 3%, [stock_price: {stock_price}, latest_price: {old_price}, quantity: {quantity}]")
                
                # for averaging 20% of ltp
                if last_traded_price <= (stock_price * 0.8):
                    holding[holding['stock'] == stock_name]['ltp'] = stock_price
                    # buy per_stock_investment/stock_price
                    count= int(per_stock_investment / stock_price)
                    # old_quantity += count
                    holding[holding['stock'] == stock_name]['quantity'] = old_quantity + count
                    # average the price
                    _price = ((old_price * old_quantity) + (stock_price * count)) / (old_quantity + count)
                    holding[holding['stock'] == stock_name]['avg_price'] = _price
                    # trade no
                    holding[holding['stock'] == stock_name]['trans_no'] = _trans_no
                    # data edit to holding
                    holding[holding['stock'] == stock_name]['date'] = date
                    # edit last_traded_price
                    holding[holding['stock'] == stock_name]['ltp'] = stock_price
                    # deduct frrom portfolio balance
                    portfolio_value -= count * stock_price
                    # now add to tranaction
                    # 'date','stock','avg_price', 'ltp','signal','quantity','profit', 'days_holding', 'balance', 'trans_no'
                    data = {'date':date, 'stock':stock_name, 'avg_price':_price, 'ltp':stock_price, 'signal':'avg', 'quantity':count, 'profit':0, 'days_holding':0, 'balance':portfolio_value, 'trans_no':_trans_no}
                    tranaction.loc[len(tranaction)] = data
                    print(f"average the price for {stock_name} to {stock_price} and quantity to {count} and price {_price}")

            # add to holding
            if row['ShortName'] not in holding['stock'].tolist() and temp_hold <= max_stock_per_day : # and portfolio_value >= per_stock_investment:
                stock_price = float(row['close'])
                count = int(round(per_stock_investment / stock_price))
                # add to holding
                holding.loc[len(holding)] = {'date':date, 'stock':row['ShortName'], 'price':stock_price, 'signal':'buy', 'quantity':count, 'trans_no':trans_no}
                # holding = holding.append({'date':date, 'stock':row['ShortName'], 'price':stock_price, 'signal':'buy', 'quantity':count}, ignore_index=True)
                temp_hold -= 1
                # remove portfolio balance
                portfolio_value -= count * stock_price
                # add to tranaction
                tranaction.loc[len(tranaction)] = {'date':date, 'stock':row['ShortName'], 'avg_price':stock_price, 'ltp':stock_price, 'signal':'buy', 'quantity':count, 'profit':0, 'days_holding':0, 'balance':portfolio_value, 'trans_no':trans_no}
                # tranaction = tranaction.append({'date':date, 'stock':row['ShortName'], 'price':stock_price, 'signal':'buy', 'quantity':count, 'profit':0, 'days_holding':0}, ignore_index=True)
                # print(f"Added {row['ShortName']} to holding")
                trans_no += 1
                # print(f"stock: {row['ShortName']} price: {stock_price} quantity: {count} holding: {holding}")

    # print(tranaction)
    return tranaction

           

        
def sample_data_print(df:pd.DataFrame, name_of_etf:str, row_number:int) -> None:
    df = df[df['ShortName'] == name_of_etf]
    # split from row  and show the first 15 and last 15
    df = df.reset_index(drop=True)
    print(f"{name_of_etf}:\n{df.iloc[row_number - 15:row_number + 15]}")

        

        


if __name__ == '__main__':
    etf_list = get_data()
    df = data_read(etf_list)
    # print(df.head())
    # print(df['ShortName'].unique())
    df.to_csv('MTF_PORTFOLIO/data/total_etf_data.csv', index=False)
    # print(df.head())
    df = pd.read_csv('MTF_PORTFOLIO/data/total_etf_data.csv')
    # print(df.head())
    data:pd.DataFrame = portfolio_analysis(df)
    data.to_csv('MTF_PORTFOLIO/portfolio_analysis.csv', index=False)
    df = pd.read_csv('MTF_PORTFOLIO/data/total_etf_data.csv')
    sample_data_print(df, 'UTINEX', 380)