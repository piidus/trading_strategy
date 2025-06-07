import pandas as pd
import os, json
from datetime import datetime



TOTAL_FUND = 15_00_000
PER_STOCK_INVEST = 15_000
PER_DAY_LIMIT = 3
HOLDING_FILE = 'MTF_PORTFOLIO/holdings.json'
# DataFrames to hold current holdings and transactions

transaction = pd.DataFrame(columns=['date', 'stock', 'avg_price', 'ltp', 'signal', 'quantity', 'profit', 'days_holding','no_of_holds', 'balance', 'trans_no'])

trans_no = 0
no_fund = 0

def save_holding(holding: pd.DataFrame):
    """Save the current holdings to a JSON file."""
    holding.to_json(HOLDING_FILE, orient='records', date_format='iso', index=False, indent=4)


def load_holding() -> pd.DataFrame:
    
    """Loads the current holdings from a JSON file.

    If the file does not exist or is empty, creates a dummy JSON file with the column names.
    Returns a DataFrame with the holdings data.
    """
    if os.path.exists(HOLDING_FILE):
        # Load holdings from the JSON file
        if os.path.getsize(HOLDING_FILE) > 0:
            return pd.read_json(HOLDING_FILE, orient='records', convert_dates=['date'])
        else:
            # create a dummy json file
            holding = [
                            {
                                "date":(pd.Timestamp.now()+pd.Timedelta(days=10000)).strftime('%Y-%m-%d %H:%M:%S'),
                                "stock":"stock",
                                "avg_price":"avg_price",
                                "ltp":"ltp",
                                "signal":"signal",
                                "quantity":"quantity",
                                "trans_no":"trans_no"
                            }
                        ]
            with open(HOLDING_FILE, 'w') as f:
                json.dump(holding, f)
        return pd.read_json(HOLDING_FILE, orient='records', convert_dates=['date'])
    else:
        return pd.DataFrame(columns=['date', 'stock', 'avg_price', 'ltp', 'signal', 'quantity', 'trans_no'])


def add_to_holding(new_record: dict):
    """Add a new record to holdings.json."""
    holding = load_holding()
    new_data = pd.DataFrame([new_record])
    holding = pd.concat([holding, new_data], ignore_index=True)
    save_holding(holding)


def update_holding(stock_name: str, updates: dict):
    """Update specific stock information in holdings.json."""
    holding = load_holding()
    if stock_name in holding['stock'].values:
        for column, value in updates.items():
            holding.loc[holding['stock'] == stock_name, column] = value
        save_holding(holding)

def delete_holding(stock_name: str):
    """Delete a specific stock from holdings.json."""
    holding = load_holding()
    holding = holding[holding['stock'] != stock_name]
    save_holding(holding)

def count_holding() -> int:
    holding = load_holding()
    return len(holding)

def buy_stock(row, holding: pd.DataFrame, signal='buy'):
    """Handles stock purchase logic."""
    global trans_no, TOTAL_FUND, no_fund
    stock_name = row['ShortName']
    today_price = row['close']
    quantity = int(PER_STOCK_INVEST / today_price)
    no_of_holds = count_holding()
    if TOTAL_FUND >= (today_price * quantity):
        # Update holdings
        holding_data = {
            'date': row['datetime'],
            'stock': stock_name,
            'avg_price': today_price,
            'ltp': today_price,
            'signal': signal,
            'quantity': quantity,
            'trans_no': trans_no
        }
        add_to_holding(new_record=holding_data)
        TOTAL_FUND -= (today_price * quantity)
        # Log transaction
        transaction.loc[len(transaction)] = {
            'date': row['datetime'],
            'stock': stock_name,
            'avg_price': today_price,
            'ltp': today_price,
            'signal': signal,
            'quantity': quantity,
            'profit': 0,
            'days_holding': 0,
            'balance': TOTAL_FUND,
            'trans_no': trans_no,
            'no_of_holds': no_of_holds
        }

        # Adjust global variables
        
        trans_no += 1

    else:
        no_fund += 1
        print(f"Insufficient funds for {stock_name} at {today_price} ({no_fund} times, day {row['datetime']}) - holding {count_holding()} stocks")
        # add to transaction
        # transaction.loc[len(transaction)] = {
        #     'date': row['datetime'],
        #     'stock': stock_name,
        #     'avg_price': today_price,
        #     'ltp': today_price,
        #     'signal': 'miss',
        #     'quantity': quantity,
        #     'profit': 0,
        #     'days_holding': 0,
        #     'balance': TOTAL_FUND,
        #     'trans_no': no_fund,
        #     'no_of_holds': no_of_holds
        # }

    return holding

def sell_stock(row, holding: pd.DataFrame, signal='sell'):
    """Handles stock selling logic."""
    global TOTAL_FUND, PER_STOCK_INVEST
    stock_name = row['ShortName']
    today_price = row['close']
    no_of_holds = count_holding()

    if stock_name in holding['stock'].values:
        stock_data = holding[holding['stock'] == stock_name].iloc[0]
        avg_price = stock_data['avg_price']
        quantity = stock_data['quantity']
        trans_id = stock_data['trans_no']
        profit = (today_price - avg_price) * quantity # * (quantity * 3)
        TOTAL_FUND += ((today_price * quantity) + (profit * 1))
        # if signal == 'avg' in stock_data['signal']:
        holding_signal = stock_data['signal']
        if holding_signal == 'buy':            
            # 3% profit
            _trade_value = (avg_price * quantity)
            _profit = (_trade_value * 0.03)
            
            PER_STOCK_INVEST += round((profit / 100), 2)
      
        # reduce PER_STOCK_INVEST
        # if PER_STOCK_INVEST >= 2_10_000:
        #     PER_STOCK_INVEST = 2_0_000
        days_holding = (row['datetime'] - pd.to_datetime(stock_data['date'])).days

        # Log transaction
        transaction.loc[len(transaction)] = {
            'date': row['datetime'],
            'stock': stock_name,
            'avg_price': avg_price,
            'ltp': today_price,
            'signal': signal,
            'quantity': quantity,
            'profit': profit,
            'days_holding': days_holding,
            'balance': TOTAL_FUND,
            'trans_no': trans_id,
            'no_of_holds': no_of_holds
        }

        # Remove stock from holdings
        delete_holding(stock_name)
    return holding


def average_stock(row, holding: pd.DataFrame, signal='avg'):
    """Handles stock average logic."""
    global TOTAL_FUND
    stock_name = row['ShortName']
    today_price = row['close']
    
    if stock_name in holding['stock'].values:
        stock_data = holding[holding['stock'] == stock_name].iloc[0]
        last_avg_price = stock_data['avg_price']
        quantity = stock_data['quantity'] + int(PER_STOCK_INVEST / today_price)
        trans_id = stock_data['trans_no']
        no_of_holds = count_holding()
        TOTAL_FUND -= ((today_price * int(PER_STOCK_INVEST / today_price)))
        # print((last_avg_price , stock_data['quantity'] ),(today_price , quantity)) , (stock_data['quantity'] , quantity)
        new_average_price = ((last_avg_price * stock_data['quantity'] )+(today_price * quantity)) / (stock_data['quantity'] + quantity)
        # UPDATE HOLDINGS
        update_holding(stock_name, {'avg_price': new_average_price, 'quantity': quantity, 'ltp': today_price})
        # Log transaction
        transaction.loc[len(transaction)] = {
            'date': row['datetime'],
            'stock': stock_name,
            'avg_price': new_average_price,
            'ltp': today_price,
            'signal': signal,
            'quantity': quantity,
            'profit': 0,
            'days_holding': 0,
            'balance': TOTAL_FUND,
            'trans_no': trans_id,
            'no_of_holds': no_of_holds
        }
    return holding


def portfolio_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analyzes portfolio and performs buy/sell operations based on conditions."""
    df['datetime'] = pd.to_datetime(df['datetime'])
    # Remove rows where close is greater than 1000
    df = df[df['close'] < 900]
    unique_dates = df['datetime'].unique()
    # print(unique_dates)
    
    # Initialize holding outside the loop to retain data
    
    
    for date in unique_dates:
        daily_data = df[df['datetime'] == date].sort_values(by='diff', ascending=True)
        temp_hold = PER_DAY_LIMIT
        holding = load_holding()

        for _, row in daily_data.iterrows():
            stock_name = row['ShortName']
            today_price = row['close']
            

            if stock_name not in holding['stock'].values and temp_hold > 0:
                holding = buy_stock(row, holding)
                temp_hold -= 1
            elif stock_name in holding['stock'].values:
                avg_price = holding.loc[holding['stock'] == stock_name, 'avg_price'].values[0]
                __quantity = holding.loc[holding['stock'] == stock_name, 'quantity'].values[0]
                stock_date = pd.to_datetime(holding.loc[holding['stock'] == stock_name, 'date'].values[0])
                stock_signal = holding.loc[holding['stock'] == stock_name, 'signal'].values[0]
                if today_price >= avg_price * 1.03:
                    holding = sell_stock(row, holding)
                # if date is olderthan 41 days  and signal is not deliver
                # elif (pd.to_datetime(date) - pd.to_datetime(holding['date'].values[0])).days >= 41 and holding['signal'].values[0] != 'deliver':
                    
                    

                elif today_price <= avg_price * 0.9:
                    # CHECK FUND AVAILABILITY
                    
                    if TOTAL_FUND >= (avg_price * __quantity):
                        holding = average_stock(row, holding)
                    else:
                        print(f"MISS AVERAGE: Date: {date}, Total Funds: {TOTAL_FUND}, Total Holdings: {len(holding)}")
        
        # print(f"Date: {date}, Total Funds: {TOTAL_FUND}, Total Holdings: {len(holding)}")

    return transaction


if __name__ == '__main__':
    start_date = 'etf2'
    input_file = 'MTF_PORTFOLIO/data/total_etf_data.csv'
    output_file = f'MTF_PORTFOLIO/portfolio_analysis_{start_date}.csv'

    if os.path.exists(input_file):
        data = pd.read_csv(input_file)
        
        # data = data[data['datetime'] >= start_date]
        result = portfolio_analysis(data)
        result.to_csv(output_file, index=False)
        df = pd.read_json(HOLDING_FILE, orient='records', convert_dates=['date'])
        df.to_csv('MTF_PORTFOLIO/holdings2.csv', index=False)
        # empty json file containing holdings
        with open(HOLDING_FILE, 'w') as f:
            
            # create a dummy json file
            holding = [
                            {
                                "date":(pd.Timestamp.now()+pd.Timedelta(days=10000)).strftime('%Y-%m-%d %H:%M:%S'),
                                "stock":"stock",
                                "avg_price":"avg_price",
                                "ltp":"ltp",
                                "signal":"signal",
                                "quantity":"quantity",
                                "trans_no":"trans_no"
                            }
                        ]
            json.dump(holding, f)
        

        # holding.to_csv('MTF_PORTFOLIO/holdings2.csv', index=False)
        print(f"Portfolio analysis saved to {output_file}")
    else:
        print(f"Input file not found: {input_file}")
