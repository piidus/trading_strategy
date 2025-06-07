try:
    import pandas as pd
    import os
    import datetime as dt
    from breeze_connect import BreezeConnect
except Exception as e:
    print('[colloect_data.py - import error::]',e)
def get_historical_data_v2( connection, from_date, to_date, stock_code, interval = "1day", exchange_code='NSE', product_type='cash') -> pd.DataFrame:
    '''
    Get historical data from BreezeConnect
    :param from_date: Start date
    :param to_date: End date
    :param stock_code: Stock code
    :param interval: Interval
    :param exchange_code: Exchange code
    :param product_type: Product type
    :return: DataFrame

    '''
    try:
        h_data = connection.get_historical_data_v2(interval=interval,
                                    from_date= from_date,
                                    to_date= to_date,
                                    stock_code=stock_code,
                                    exchange_code=exchange_code,
                                    product_type=product_type)
    except Exception as e:
        print(e)
    else:
    # print(h_data)
        if h_data['Status'] == 200:
            df = pd.DataFrame(h_data['Success'])
            # if df is not null
            if df is not []:
                df = df[[ 'datetime', 'open','high','low', 'close', 'volume']]
                # datetime as datetime format
                df['datetime'] = pd.to_datetime(df['datetime'])
                # print(df.head(10))
                return df
            else:
                print('df is null')
        else:
            print(h_data['Error'])
            return -1

def collect_historical_data(connection,stock_code: str = 'NIFTY', interval: str = '1day') -> dict:
    total_data = pd.DataFrame()
    try:
        from_date:  str = (dt.date.today() - dt.timedelta(days =365*5)).strftime('%Y-%m-%dT%H:%M:%S')
        to_date : str = dt.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        while True:
            # Fetch historical data
            df = get_historical_data_v2(connection=connection, from_date=from_date, to_date=to_date, stock_code=stock_code, interval=interval)
            # Add the fetched data to the total dataset
            total_data = pd.concat([df, total_data], axis=0, ignore_index=True)

            # Check if the earliest date in the fetched data is still after the start date
            if not df.empty:       

                first_date = pd.to_datetime(df['datetime'].iloc[0])
                if first_date <= pd.to_datetime(from_date):
                    # print(f'[Data fetched for {stock_code} up to {first_date}]')
                    break

                # Update the `to_date` to fetch earlier data
                to_date = (first_date - dt.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
                # print(f'[Fetching data until {to_date}]')
            else:
                break

    except Exception as e:
        print(f'[Error]: {e}')

    return total_data
def get_etf_data():
    
    """
    Function to collect ETF data from NSEScripMaster.txt
    
    Read the NSEScripMaster.txt file, filter the data for the required columns, 
    drop any records with missing values in CompanyName or Token, and then filter 
    the data for ETFs by selecting the records where CompanyName ends with 'ETF'. 
    
    The final data is then written to a csv file called etf_list.csv in the MTF_PORTFOLIO directory.
    """
    df = pd.read_csv('data/NSEScripMaster.txt')
    # df.head()
    # remove all " from the column names and remove spaces
    df.columns = df.columns.str.replace('"', '')
    df.columns = df.columns.str.replace(' ', '')
    selected_columns = ['Token', 'ShortName', 'Series', 'CompanyName', 'FaceValue','ISINCode','MarginPercentage', 'ExchangeCode']
    # filter series = EQ
    df = df[df['Series'] == 'EQ']
    df = df[selected_columns]
    df = df.dropna(subset=['CompanyName', 'Token'])
    # drop where token is 0
    df = df[df['Token'] != '0']
    # find etf where company name end with ETF
    # df = df[df['CompanyName'].str.endswith('ETF')].reset_index(drop=True)
     # Define regular expressions to match 'ETF' with a space before or after
    pattern1 = r"\sETF"  # Match 'ETF' with a space before
    pattern2 = r"ETF\s"  # Match 'ETF' with a space after

    # Filter the DataFrame using the regular expressions
    df = df[df['CompanyName'].str.contains(pattern1) | df['CompanyName'].str.contains(pattern2)]

    print(df.head(10))
    df.to_csv('MTF_PORTFOLIO/etf_list.csv', index=False)


def collect_etf_data():
    api_key = os.getenv('API_KEY')
    secret_key = os.getenv('API_SECRET')
    session = os.getenv('API_SESSION')
    breeze = BreezeConnect(api_key=api_key)
    breeze.generate_session(api_secret=secret_key, session_token=session)
    connection = breeze
    print('Connected to the Breeze!', connection)
    
    df = pd.read_csv('MTF_PORTFOLIO/etf_list.csv')
    for index, row in df.iterrows():
        print(row['ShortName'], row['ShortName'], row['CompanyName'])
        data =collect_historical_data(connection=connection, stock_code=row['ShortName'], interval='1day')
        data['ShortName'] = row['ShortName']
        data['CompanyName'] = row['CompanyName']
        # data.to_csv(f'MTF_PORTFOLIO/data/{row["ShortName"]}.csv', index=False)
        print(f"Data saved to {row['CompanyName']} ")
if __name__ == '__main__':
    get_etf_data()
    collect_etf_data()