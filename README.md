# Algorithmic Stock Trading

Welcome to the Algorithmic Stock Trading project! This project involves the design and implementation of an algorithmic trading system aimed at automating trade execution. By leveraging real-time market data analysis and predefined criteria, the system optimizes trading strategies to minimize errors and biases.

## Features

- **Automated Trade Execution**: Integrates with the Zerodha API to execute trades automatically based on predefined strategies.
- **Real-Time Market Data Analysis**: Processes live market data to make informed trading decisions.
- **Predefined Trading Criteria**: Utilizes specific criteria to guide trading decisions, reducing human error and emotional bias.

## Project Structure:
    
    algorithmictrading/
    ├── app.py                  # Main entry point for the application
    ├── bscount.csv             # CSV file tracking buy and sell counts
    ├── data/                   # Directory containing user-related data
    │   └── userdata.csv         # User data for API integration
    ├── modules/                # Contains core Python modules
    │   ├── __init__.py          # Initializes the module
    │   ├── auth.py              # Handles user authentication and token validation
    │   ├── historical_data.py   # Fetches historical stock data using the KiteConnect API
    ├── static/                 # Contains static files like CSS
    │   └── styles.css           # Stylesheet for the application
    ├── templates/              # HTML templates for the web interface
    │   ├── backtest.html        # Backtesting page
    │   ├── fetch_data.html      # Data fetching page
    │   ├── index.html           # Homepage
    │   └── ...                  # Other HTML pages (login, error, setup, etc.)

## Prerequisites
1. **API Credentials:**
Create a file named userdata.csv in the data/ directory with the following columns:
api_key
access_token
user_id
public_token

Example of userdata.csv:

    api_key,access_token,user_id,public_token
    your_api_key,your_access_token,your_user_id,your_public_token


3. **Database Initialization:**
Ensure a file named bscount.csv exists in the project root directory. It should contain the following initial data:
    ```css
    bcount,scount,last_order_price,last_order_placed
    0,0,none,none

## Tech Stack

- **Backend**: Python
- **Frontend**: HTML, CSS, JavaScript
- **API**: Zerodha API

## Installation

To get started with the project, follow these steps:

1. **Clone the repository:**
   ```
   git clone https://github.com/subha0319/AlgorithmicStockTrading.git
   cd AlgorithmicStockTrading
2. **Set Up a Virtual Environment (Optional):**
   ```
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use venv\Scripts\activate
3. **Install Dependencies:** Ensure that you have a requirements.txt file that includes all necessary Python packages.
   ```
   pip install -r requirements.txt
4. **Configure API Access:**
- Obtain API credentials from Zerodha.
- Ensure userdata.csv is placed in the data/ directory with valid credentials from Zerodha.

5. Database Initialization:
- Verify that bscount.csv exists in the project root and is initialized with valid data.

6. **Run the Application:**
   ```
   python app.py

## Modules Description
- auth.py: Handles authentication and validates user tokens using the KiteConnect API.
- historical_data.py: Fetches historical stock data for a specified time range using the KiteConnect API.

## Common Issues
- If the error "Run setup.py" appears, ensure userdata.csv exists and contains valid API credentials.
- Check that bscount.csv is initialized with valid data.
