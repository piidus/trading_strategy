try:
    import pandas as pd
    import os
    import datetime as dt
    import yfinance as yf


except Exception as e:
    print('[colloect_data.py - import error::]',e)


def collect_historical_data(stock_code: str = 'NIFTY', interval: str = '1day') -> dict:
    total_data = pd.DataFrame()
    try:
        from_date:  str = (dt.date.today() - dt.timedelta(days =365*15)).strftime('%Y-%m-%dT%H:%M:%S')
        to_date : str = dt.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        stock_code = stock_code.upper()+'.NS'
        # Fetch historical data
        df = ticker = yf.Ticker(stock_code)
        # print(ticker.financials)
        # print(ticker.get_financials().loc['TotalRevenue'])
        # history data from 2019

        df = ticker.history(start="2019-01-01", end="2024-01-01")

        # print(df)
    except Exception as e:
        print(f'[Error]: {e}')

    else:
        # data pre processing
        df['datetime'] = df.index
        return df
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
    df.to_csv('MTF_PORTFOLIO/etf_list_yahoo.csv', index=False)


def collect_etf_data():
    
    
    df = pd.read_csv('MTF_PORTFOLIO/etf_list_yahoo.csv')
    for index, row in df.iterrows():
        print(row['ShortName'], row['ShortName'], row['CompanyName'])
        data =collect_historical_data( stock_code=row['ExchangeCode'], interval='1day')
        if data.empty:
            continue
        data['ShortName'] = row['ShortName']
        data['CompanyName'] = row['CompanyName']
        data.to_csv(f'MTF_PORTFOLIO/data_yahoo/{row["ShortName"]}.csv', index=False)
        print(f"Data saved to {row['CompanyName']} ")
if __name__ == '__main__':
    # get_etf_data()
    collect_etf_data()