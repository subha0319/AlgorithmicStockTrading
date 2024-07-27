import threading
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from kiteconnect import KiteConnect
import pandas as pd
import os, csv
import datetime
import time
from modules import auth
import numpy as np
import logging


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Define the global variable
is_trading = False

# Path to store user data
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
USERDATA_FILE = os.path.join(DATA_PATH, 'userdata.csv')


def load_user_data():
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
    if not os.path.exists(USERDATA_FILE):
        initial_data = {
            'api_key': [''],
            'api_secret': [''],
            'user_name': [''],
            'access_token': [''],
            'token_req_date': [''],
            'user_id': [''],
            'public_token': ['']
        }
        pd.DataFrame(initial_data).to_csv(USERDATA_FILE, index=False)
    else:
        # Check if the file is empty
        if os.stat(USERDATA_FILE).st_size == 0:
            # File is empty, add the column names as the first row
            column_names = ['api_key', 'api_secret', 'user_name', 'access_token', 
                            'token_req_date', 'user_id', 'public_token']
            pd.DataFrame(columns=column_names).to_csv(USERDATA_FILE, index=False)

def get_user_data():
    if os.path.exists(USERDATA_FILE):
        try:
            userdata = pd.read_csv(USERDATA_FILE)
            # Check if the file is empty
            if userdata.empty:
                # If the file is empty, add the missing columns
                load_user_data()
            else:
                required_columns = ['api_key', 'api_secret', 'user_name', 'access_token', 
                                    'token_req_date', 'user_id', 'public_token']
                # Check if all required columns are present
                if all(col in userdata.columns for col in required_columns):
                    # Return the first row
                    return userdata.iloc[0]
                else:
                    # If any required column is missing, add them
                    load_user_data()
        except pd.errors.EmptyDataError:
            # If the file is empty or cannot be read, add the missing columns
            load_user_data()
    else:
        # If the file does not exist, create it and return None
        load_user_data()


def save_user_data(api_key, api_secret, user_name, access_token, token_req_date, user_id, public_token):
    userdata = pd.DataFrame({'api_key': [api_key], 'api_secret': [api_secret], 
                             'user_name': [user_name], 'access_token': [access_token], 
                             'token_req_date': [token_req_date], 'user_id': [user_id], 
                             'public_token': [public_token]})
    userdata.to_csv(USERDATA_FILE, index=False)

def generate_login_url(api_key, api_secret):
    global kite
    kite = KiteConnect(api_key=api_key)
    return kite.login_url()

# Function to extract the request token from the URL
def extract_request_token(url):
    # Split the URL by "&" to separate parameters
    params = url.split('&')
    
    # Loop through each parameter to find the one containing the request token
    for param in params:
        if 'request_token=' in param:
            # Extract the request token value
            request_token = param.split('request_token=')[-1]
            return request_token
    
    # If request token is not found, return None
    return None

def generate_access_token(request_token, api_secret):
    data = kite.generate_session(request_token, api_secret)
    return data

def validate_access_token(access_token):
    try:
        kite.set_access_token(access_token)
        profile_data = kite.profile()
        return profile_data
    except Exception as e:
        print("Error validating access token:", e)
        return None
    
def clear_user_data():
    if os.path.exists(USERDATA_FILE):
        userdata = get_user_data()
        if userdata is not None:
            # Clear user data by overwriting the file with an empty DataFrame
            pd.DataFrame(columns=userdata.index).to_csv(USERDATA_FILE, index=False)

def calculate_ma(data):
    if not data:
        return None
    return round(sum(data) / len(data),2)

def trading_strategy(current_price, ma, kite, token, last_order_price, last_order_placed, bcount, scount, bars):
    if last_order_price is None:
        last_order_price = "none"
    if last_order_placed is None:
        last_order_placed = "none"
    
    #days = 25
    #portfolio = 2000
    stop_loss = 50000
    take_profit = 10000
    quantity = 1

    if current_price > ma:
        bcount += 1
    else:
        bcount = 0
    if current_price < ma:
        scount += 1
    else:
        scount = 0

    userdata = auth.get_userdata()
    kite = KiteConnect(api_key=userdata['api_key'])
    kite.set_access_token(userdata['access_token'])

    current_time = datetime.datetime.now()
    if  last_order_placed == "BUY" and current_time.time() >= datetime.datetime.time(22, 59):
        logging.info("Time is 10:59 PM, selling stocks...")
        kite.place_order(
                variety=kite.VARIETY_REGULAR,
                exchange=kite.EXCHANGE_MCX,
                tradingsymbol="SILVERMIC24JUNFUT",
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=quantity,
                product=kite.PRODUCT_MIS,
                order_type=kite.ORDER_TYPE_MARKET
            )
        last_order_placed = "SELL"

    elif bcount>=bars and (last_order_placed == "SELL" or last_order_placed is None) and current_time.time() <= datetime.time(22, 59):
            logging.info
            kite.place_order(
                variety=kite.VARIETY_REGULAR,
                exchange=kite.EXCHANGE_MCX,
                tradingsymbol="SILVERMIC24JUNFUT",
                transaction_type=kite.TRANSACTION_TYPE_BUY,
                quantity=quantity,
                product=kite.PRODUCT_MIS,
                order_type=kite.ORDER_TYPE_MARKET
            )
            last_order_placed = "BUY"
            last_order_price = current_price
            print("Stocks are bought")
            print("Price: "+ current_price*quantity)

    elif last_order_placed == "BUY":
        if last_order_price * quantity - current_price * quantity >= stop_loss:
            logging.info("Placing a new Sell Order (Stop Loss Hit)")
            kite.place_order(
                variety=kite.VARIETY_REGULAR,
                exchange=kite.EXCHANGE_MCX,
                tradingsymbol="SILVERMIC24JUNFUT",
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=quantity,
                product=kite.PRODUCT_MIS,
                order_type=kite.ORDER_TYPE_MARKET
            )
            last_order_placed = "SELL"
            print("Stocks are sold due to stop loss")
            print("Price: "+ current_price*quantity)
        elif current_price * quantity - last_order_price * quantity >= take_profit:
            logging.info("Placing a new Sell Order (Take Profit Hit)")
            kite.place_order(
                variety=kite.VARIETY_REGULAR,
                exchange=kite.EXCHANGE_MCX,
                tradingsymbol="SILVERMIC24JUNFUT",
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=quantity,
                product=kite.PRODUCT_MIS,
                order_type=kite.ORDER_TYPE_MARKET
            )
            last_order_placed = "SELL"

        elif scount >= bars:
            logging.info("Placing a new Sell Order (Condition hit)")
            kite.place_order(
                variety=kite.VARIETY_REGULAR,
                exchange=kite.EXCHANGE_MCX,
                tradingsymbol="SILVERMIC24JUNFUT",
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=quantity,
                product=kite.PRODUCT_MIS,
                order_type=kite.ORDER_TYPE_MARKET
            )
            last_order_placed = "SELL"
            #transaction+= 1
    
    with open("bscount.csv", 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow([bcount,scount,last_order_price,last_order_placed])

def real_strategy(token):
    userdata = auth.get_userdata()
    kite = KiteConnect(api_key=userdata['api_key'])
    kite.set_access_token(userdata['access_token'])

    global is_trading
    
    if is_trading:
        print("Trading Started")

    while is_trading:
        bars = 10
        
        while True:
            current_time = datetime.datetime.now()

            if datetime.time(9, 00) <= current_time.time() <= datetime.time(23, 00):
                minutes = 20*15
                with open('bscount.csv', 'r') as file:
                    reader = csv.reader(file)
                    row=next(reader)
                    bcount = int(row[0])
                    scount = int(row[1])
                    last_order_price = row[2]
                    last_order_placed = row[3]

                # Fetch historical data for the past 30 minutes
                start_time = current_time - datetime.timedelta(minutes=minutes)
                historical_data = kite.historical_data(token, start_time, current_time, "15minute")
                if historical_data:
                    #print('first record:', historical_data[0])

                # Extract closing prices for the past 30 minutes
                    minute_closes = [record['close'] for record in historical_data]
                    #print(minute_closes)

                    # Calculate moving average for the past minute
                    ma = calculate_ma(minute_closes)

                    # Execute trading strategy every 30 minutes
                    last_price = historical_data[-1]['close']  # Get the latest price for the current minute
                    trading_strategy(last_price, ma, kite, token, last_order_price, last_order_placed, bcount, scount, bars)

                # Wait for the next 30 minutes
                minutes = 15
                next_time = current_time + datetime.timedelta(minutes=minutes)
                time_to_wait = next_time - datetime.datetime.now()
                time_to_wait_seconds = time_to_wait.total_seconds()
                if time_to_wait_seconds > 0:
                    logging.info(f"Waiting for next minute: {time_to_wait_seconds} seconds")
                    time.sleep(time_to_wait_seconds)
            else:
                # Outside market hours
                logging.info("Market is closed...")
                is_trading = False
                break

        # Check if trading is still active
        if not is_trading:
            print("Trading Stopped")
            break

def strategy(records, portfolio_value):
    check=0
    bcount=0
    scount=0
    bars=8
    last_order_placed = None
    days = 12
    ma = 0
    sum_close = 0
    amount = portfolio_value
    stop_loss = 50000
    take_profit = 10000
    transaction = 0
    transac_date = []
    portfolio_val = []
    quantity = 10
    
    for idx, record in enumerate(records):
        if idx < days:
            sum_close += record['close']
            continue
        ma = sum_close / days
        sum_close -= records[idx - days]['close']
        sum_close += record['close']
        if record['close']>ma:
            bcount+=1
        else:
            bcount=0
        if record['close']<ma:
            scount+=1
        else:
            scount=0
        if bcount>=bars and (last_order_placed == "SELL" or last_order_placed is None) and record['date'].time() <= datetime.time(22, 59):
            print("Place a new BUY Order")
            print('price:',(record['close']))
            portfolio_value-=record['close']*quantity 
            last_order_price = record['close']                 
            last_order_placed = "BUY"
            transaction += 1
            check=1
        elif last_order_placed == "BUY":
            current_price = record['close']
            if  record['date'].time() >= datetime.time(22, 59):
                print("Place a new Sell Order (Intraday hit)")
                portfolio_value += current_price * quantity
                print(portfolio_value)
                last_order_placed = "SELL"
                transaction += 1
                check=1
            elif (last_order_price*quantity)-(current_price*quantity) >= stop_loss:
                # Sell due to stop loss
                print("Place a new Sell Order (Stop Loss Hit)")
                portfolio_value += current_price * quantity
                print(portfolio_value)
                last_order_placed = "SELL"
                transaction += 1
                check=1

            elif current_price*quantity - last_order_price*quantity >= take_profit:
                # Sell due to take profit
                print("Place a new Sell Order (Take Profit Hit)")
                portfolio_value += current_price * quantity
                print(portfolio_value)
                last_order_placed = "SELL"
                transaction += 1
                check=1
            elif idx == len(records) - 1:
                last_order_placed = "SELL"
                print(record['close'])
                print("Place a new Sell Order(end of records hit)")
                portfolio_value+=record['close']*quantity
                transaction+=1
                check=1
                transac_date.append(record['date'].date())
                portfolio_val.append(portfolio_value)
            elif scount>=bars:   
                #Calculate Profit again
                print("Place a new Sell Order(condition hit)")
                print(record['close'])
                portfolio_value+=record['close']*quantity   
                print(portfolio_value)                           
                last_order_placed = "SELL"
                transaction+=1
                transac_date.append(record['date'].date())
                portfolio_val.append(portfolio_value)
                check=1
        # Record transaction details
        if(check==1):
            row = [transaction, last_order_placed, record['date'], round(record['close'] * quantity, 2)]
            with open("backtest_result.csv", 'a', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(row)
        check=0
    # Calculate profit percentage
    profit_percent = ((portfolio_value - amount) / amount) * 100
    row1 = ['profit_percent', 'profit']
    row2 = [round(profit_percent, 2), round(portfolio_value - amount, 2)]
    with open("backtest_result.csv", 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(row1)
        csvwriter.writerow(row2)
    for val, date in zip(portfolio_val, transac_date):
        row = ['portfolio_value', 'transaction_date']
        row_data = [val, date]
        with open("backtest_result.csv", 'a', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(row)
            csvwriter.writerow(row_data)

def read_records(start_datetime, end_datetime):
    filename = "backtest_result.csv"
    with open(filename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['transaction_no', 'buy/sell', 'date', 'price'])
    df = pd.read_csv('data/fetched_data.csv')  # Adjust path for intraday data
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    filtered_df = df[(df['date'] >= start_datetime) & (df['date'] <= end_datetime)]
    records = filtered_df.to_dict('records')
    return records

# Define a function to start the trading strategy in a separate thread
def start_strategy(token):
    global is_trading
    is_trading = True
    real_strategy(token)


@app.route('/')
def index():
    # Check if userdata.csv exists and is not empty
    userdata = get_user_data()
    if userdata is None:
        # If userdata.csv is empty or incomplete, redirect to setup
        return redirect(url_for('setup'))
    else:
        if 'access_token' in userdata:
            access_token = userdata['access_token']
            token_req_date_str = str(userdata['token_req_date'])
            if token_req_date_str != 'nan':
                token_req_date = datetime.datetime.strptime(token_req_date_str, "%Y-%m-%d %H:%M:%S")
                # Check if the access token is not expired
                if not validate_access_token(access_token):  # validity of access token is 1 day
                    return redirect(url_for('trade'))
                else:
                    # If access token is expired, redirect to login page
                    return redirect(url_for('login'))
            else:
                # If token_req_date is 'nan', redirect to login
                return redirect(url_for('login'))
        else:
            # Redirect to login if API key and secret are present but access token is missing
            return redirect(url_for('login'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        api_key = request.form['api_key']
        api_secret = request.form['api_secret']
        save_user_data(api_key, api_secret, '', '', '', '', '')  # Initialize additional fields with empty values
        return redirect(url_for('index'))
    else:
        return render_template('setup.html')

@app.route('/validate-token', methods=['POST'])
def validate_token():
    request_token_link = request.form['request_token_link']
    request_token = extract_request_token(request_token_link)  # Use the function to extract request token
    if request_token:
        access_token_data = generate_access_token(request_token, get_user_data()['api_secret'])
        if access_token_data:
            profile_data = validate_access_token(access_token_data['access_token'])
            if profile_data:
                # Extract required information from profile_data
                user_name = profile_data['user_name']
                user_id = profile_data['user_id']
                public_token = access_token_data['public_token']
                token_req_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                                # Save user data including additional information
                api_key, api_secret, _, _, _, _, _ = get_user_data()
                save_user_data(api_key, api_secret, user_name, access_token_data['access_token'], 
                               token_req_date, user_id, public_token)

                return render_template('login_success.html')
            else:
                return render_template('login_failure.html', message="Error validating access token.")
        else:
            return render_template('login_failure.html', message="Error generating access token.")
    else:
        return render_template('login_failure.html', message="Request token not found in URL parameters.")

# Modify the start_trading() endpoint to start the strategy in a separate thread
@app.route('/start-trading', methods=['POST'])
def start_trading():
    global is_trading
    token = 109134855
    
    # Start the strategy in a separate thread
    threading.Thread(target=start_strategy, args=(token,), daemon=True).start()
    
    # Return a JSON response indicating that trading has started
    return jsonify({'is_trading': is_trading, 'button_text': 'Stop Algo Trading', 'button_color': '#ff6347'})

@app.route('/stop-trading', methods=['POST'])
def stop_trading():
    global is_trading
    is_trading = False
    return jsonify({'is_trading': is_trading})

@app.route('/trade.html')
def trade():
    # Redirect to the trade page after fetching, saving data, and performing backtesting
    return render_template('trade.html')

@app.route('/login')
def login():
    # Render the login.html template with the login URL
    userdata = get_user_data()
    if userdata is not None:
        login_url = generate_login_url(userdata['api_key'], userdata['api_secret'])
        # Store the API secret in the session
        session['api_secret'] = userdata['api_secret']
        return render_template('login.html', login_url=login_url)
    else:
        # If user data is missing or incomplete, redirect to setup
        return redirect(url_for('setup'))

@app.route('/backtest')
def backtest_page():
    return render_template('backtest.html')

@app.route('/start-backtest', methods=['GET','POST'])
def start_backtest():
    if request.method == 'POST':
        # Extract input data from the HTML form
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        portfolio_value = float(request.form['portfolio_value'])

        # Convert start_date and end_date strings to datetime64 objects
        startdate = np.datetime64(datetime.datetime.strptime(start_date, "%Y-%m-%d"))
        enddate = np.datetime64(datetime.datetime.strptime(end_date, "%Y-%m-%d"))
        
        # Perform backtesting
        try:
            records = read_records(startdate, enddate)
            strategy(records, portfolio_value)
            
            return render_template('backtest.html')
        except Exception as e:
            return f"Error during backtesting: {str(e)}"
    else:
        return render_template('backtest_form.html')

@app.route('/fetch_data', methods=['GET', 'POST'])
def fetch_data():
    # Initialize Kite Connect
    userdata = auth.get_userdata()
    kite = KiteConnect(api_key=userdata['api_key'])
    kite.set_access_token(userdata['access_token'])

    if request.method == 'POST':
        # Extract input data from the HTML form
        token = 109134855
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        time_interval = "15minute"  # Example time interval

        # Convert start_date and end_date strings to datetime objects
        startdate = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        enddate = datetime.datetime.strptime(end_date, "%Y-%m-%d")

        start_year = startdate.year
        end_year = enddate.year

        # Fetch data using the specified parameters
        try:
            all_records = []

           # Check if the number of days is greater than or equal to 200
            if (enddate - startdate).days >= 200:
                # Iterate over each year from start_year to end_year
                for year in range(start_year, end_year + 1):
                    # Define the start and end dates for the current year
                    year_start = datetime.datetime(year, 1, 1)
                    if year == start_year:
                        year_start = startdate
                    year_end = datetime.datetime(year, 12, 31)
                    if year_end > enddate:
                        year_end = enddate

                    # Fetch historical data for the current year
                    records = kite.historical_data(token, year_start, year_end, time_interval)

                    # Append the records to the list
                    if records:
                        all_records.extend(records)
                        print(f"Data fetched for year {year}")
            else:
                # Fetch historical data for the entire duration
                all_records = kite.historical_data(token, startdate, enddate, time_interval)

            # Convert the list of dictionaries to a DataFrame
            df = pd.DataFrame.from_records(all_records)

            # Save the DataFrame to a CSV file in the "data" directory
            filename = os.path.join(DATA_PATH, f"fetched_data.csv")
            df.to_csv(filename, index=False)

            # Redirect to the trade page after fetching and saving data
            return render_template('backtest.html')
        except Exception as e:
            # Return the error message to be displayed in the HTML template
            fetching_status = f"Error fetching data: {e}"
            return render_template('fetch_data.html', fetching_status=fetching_status)
    else:
        # Handle the GET request (render the fetch data page)
        return render_template('fetch_data.html')

@app.route('/logout')
def logout():
    session.clear()  # Clear the session data
    clear_user_data() # Clear the user data from the CSV file
    return redirect(url_for('setup'))

@app.route('/login/callback')
def login_callback():
    # Extract the request token from the URL
    request_token_link = request.url
    request_token = extract_request_token(request_token_link)

    if request_token:
        # Get the stored API secret from the session
        api_secret = session.get('api_secret')

        if api_secret:
            # Generate access token using the request token and API secret
            access_token_data = generate_access_token(request_token, api_secret)
            if access_token_data:
                profile_data = validate_access_token(access_token_data['access_token'])
                if profile_data:
                    # Extract required information from profile_data
                    user_name = profile_data['user_name']
                    user_id = profile_data['user_id']
                    public_token = access_token_data['public_token']
                    token_req_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Save user data including additional information
                    api_key, _, _, _, _, _, _ = get_user_data()
                    save_user_data(api_key, api_secret, user_name, access_token_data['access_token'], 
                                   token_req_date, user_id, public_token)

                    return redirect(url_for('login_success'))
                else:
                    return render_template('login_failure.html', message="Error validating access token.")
            else:
                return render_template('login_failure.html', message="Error generating access token.")
        else:
            return render_template('login_failure.html', message="API secret not found in session.")
    else:
        return render_template('login_failure.html', message="Request token not found in URL parameters.")

@app.route('/login_success')
def login_success():
    # Render the login_success.html template
    return render_template('login_success.html')

if __name__ == '__main__':
    app.run(debug=True)
