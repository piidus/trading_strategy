from breeze_connect import BreezeConnect
import pandas as pd
import datetime as dt
import time
# from backend.environ_parser import API_KEY, API_SECRET, API_SESSION
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.environ_parser import API_KEY, API_SECRET, API_SESSION



class History:
    def __init__(self, api_key, api_secret, api_session):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_session = api_session
        self.breeze: BreezeConnect = BreezeConnect(api_key=api_key)

    def connection(self):
        try:
            self.breeze.generate_session(api_secret=self.api_secret, session_token=self.api_session)
            return self.breeze
        except Exception as e:
            print(f"Error generating session: {e}")
            return None

    def get_historical_data_v2(self, from_date, to_date, stock_code, connection, interval="1day",
                                exchange_code='NSE', product_type='cash') -> pd.DataFrame:
        """
        Get historical data from BreezeConnect
        """
        try:
            h_data = connection.get_historical_data_v2(
                interval=interval,
                from_date=from_date,
                to_date=to_date,
                stock_code=stock_code,
                exchange_code=exchange_code,
                product_type=product_type
            )
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return None

        if h_data.get('Status') == 200:
            df = pd.DataFrame(h_data.get('Success', []))
            if not df.empty:
                df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
                df['datetime'] = pd.to_datetime(df['datetime'])
                return df
            else:
                print('DataFrame is empty')
                print(h_data)
                return None
        else:
            print(f"Error response: {h_data.get('Error')}")
            return None

    def fetch_data_with_retry(self, stock_code, interval):
        total_data = pd.DataFrame(columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])

        from_date_limit = (dt.date.today() - dt.timedelta(days=365 * 5)).strftime('%Y-%m-%dT%H:%M:%S')
        current_to_date = dt.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        print(f"Starting data fetch for {stock_code} from {from_date_limit} to {current_to_date}")

        breeze_connection = self.connection()
        if breeze_connection is None:
            print("Unable to establish Breeze connection. Exiting.")
            return total_data

        while True:
            try:
                df = None
                retries = 0
                max_retries = 1
                retry_delay_seconds = 50

                while df is None and retries < max_retries:
                    df = self.get_historical_data_v2(
                        from_date=from_date_limit,
                        to_date=current_to_date,
                        stock_code=stock_code,
                        interval=interval,
                        connection=breeze_connection
                    )
                    if df is None:
                        print(f"Retry {retries + 1}/{max_retries} after failure...")
                        time.sleep(retry_delay_seconds)
                        retries += 1

                if df is None:
                    print(f"Failed to fetch data for {stock_code} after {max_retries} retries.")
                    break

                if df.empty:
                    print(f"No data returned for {stock_code} before {current_to_date}. Stopping fetch.")
                    break

                df['datetime'] = pd.to_datetime(df['datetime'])
                total_data = pd.concat([total_data, df], ignore_index=True)
                total_data.drop_duplicates(subset=['datetime'], inplace=True)
                total_data.sort_values(by='datetime', inplace=True)

                first_date_in_df = total_data['datetime'].min()
                if first_date_in_df <= pd.to_datetime(from_date_limit):
                    print(f"Fetched complete data for {stock_code} up to {first_date_in_df}.")
                    break

                newly_fetched_min_date = df['datetime'].min()
                current_to_date = (newly_fetched_min_date - dt.timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%S')
                print(f"Continuing fetch for {stock_code} until {current_to_date}")

            except Exception as e:
                print(f"Unhandled exception while fetching data: {e}")
                break

        print(f"Total records fetched for {stock_code}: {len(total_data)}")
        return total_data


if __name__ == '__main__':
    nifty = History(api_key=API_KEY, api_secret=API_SECRET, api_session=API_SESSION)
    data = nifty.fetch_data_with_retry(stock_code='NIFTY', interval='1minute')
    print(data.head())
    # save data to csv
    # data.to_csv('tracked_data/nifty_data.csv', index=False)
