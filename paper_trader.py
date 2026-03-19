from stock_market_data import Stock
from pathlib import Path
import csv
from datetime import datetime
import json

#  --- File Setup ---
# ----------------------------------------------------------------------------------------------------------

# Initializes the files and if not there, makes new ones
transactions_file = Path("paper_transactions.csv")
data_file = Path("paper_data.json")

if not transactions_file.exists():
    with open(transactions_file, 'w', newline='') as f:
        writer = csv.writer(f)
        # These are the headers
        writer.writerow(['symbol', 'shares', 'price', 'time', 'type'])


# Initializes the JSON file in case the file doesn't exist so all the values stay
def initialize_data(starting_cash, fee_per_trade):
    inserted_data = {"starting_cash": starting_cash,
                     "cash": starting_cash,
                     "fee_per_trade": fee_per_trade}

    with open(data_file, 'w') as file:
        json.dump(inserted_data, file, indent=4)


if not data_file.exists():
    initialize_data(100000.00, 0.0)


# Resets all the data
def reset(starting_cash=100000.00, fee_per_trade=0.0):
    # Resets the JSON data
    initialize_data(starting_cash, fee_per_trade)

    # Clears the CSV back to just the header
    with open(transactions_file, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['symbol', 'shares', 'price', 'time', 'type'])


# --- File I/O ---
# ----------------------------------------------------------------------------------------------------------

# Gives all the rows in the log into a list and if there are empty lines, auto-cleans it
def read_transactions():
    rows = []
    original_rows = []

    # Reads all the rows, and if it is empty, it ignores it
    with open(transactions_file, 'r') as file:
        reader = csv.reader(file)

        for row in reader:
            original_rows.append(row)
            if not row:
                continue
            if len(row) != 5:
                continue
            if any(cell.strip() == "" for cell in row):
                continue
            rows.append(row)

    if rows != original_rows:
        with open(transactions_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(rows)

    return rows


# Gives all the transactions in a dictionary
def all_transactions():
    return dict_sort(read_transactions())


# Gives all the transactions of a symbol
def transactions(symbol):
    symbol = symbol.strip().upper()
    data = all_transactions()
    rows = []

    for i in data:
        if i['symbol'] == symbol:
            rows.append(i)
    return rows


# Sort each of the rows by their header
def dict_sort(rows):
    if not rows:
        return []

    header = rows[0]
    data = rows[1:]
    return [dict(zip(header, row)) for row in data]


# --- Account ---
# ----------------------------------------------------------------------------------------------------------

# Gives the data in the JSON file
def read_data():
    if not data_file.exists():
        return {}
    try:
        with open(data_file, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}


# Changes the json file by rewriting it
def write_data(data):
    with open(data_file, 'w') as file:
        json.dump(data, file, indent=4)


# Get the cash balance
def balance():
    data = read_data()
    return data.get("cash", 0.0)


# Updates the cash balance
def update_balance(amount):
    data = read_data()
    data['cash'] = round(data.get('cash', 0.0) + amount, 2)
    write_data(data)


# --- Trading ---------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------
# Checks the symbols and shares in one place
def check_transaction(symbol, shares):
    if shares is None or shares <= 0:
        return False, "Error: Amount cannot be nothing or negative"

    if shares % 1 != 0:
        return False, "Error: Amount cannot be a decimal"

    symbol = symbol.strip().upper()
    if symbol == "":
        return False, "Error: Ticker cannot be empty"

    try:
        Stock(symbol).current_price()
    except:
        return False, 'Error: Name is invalid'

    return True, ''


# Fills in the transactions and sends to CSV
def place_trade(symbol, shares, market_price):
    # Sees if the symbol is empty
    symbol = symbol.strip().upper()

    # Opens the log file and writes the transaction
    with open(transactions_file, 'a', newline='') as file:
        writer = csv.writer(file)
        # Sees if it is a buy or a sell depending on the sign, or if it is none
        trade_type = "buy" if shares > 0 else "sell"
        # Gives the time now in the following format 2026-03-05 19:41:28
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([symbol, shares, market_price, time, trade_type])


# Handles the logic to buy stocks by check if valid and then placing trade and updating balance
def buy(symbol, shares):
    valid, message = check_transaction(symbol, shares)
    if not valid:
        return False, message

    market_price = Stock(symbol).current_price()
    fee = read_data().get("fee_per_trade", 0.0)

    # If you have less cash then the cost of the transaction, or if shares less than zero it won't run
    if balance() < shares * market_price + fee:
        return False, 'You do not have enough money'

    place_trade(symbol, shares, market_price)
    # Updates the cash value, so it goes down by the cost
    update_balance(-(shares * market_price + fee))
    return True, ''


# Handles the logic to sell stocks by checking if valid and then placing trade and updating balance
def sell(symbol, shares):
    valid, message = check_transaction(symbol, shares)
    if not valid:
        return False, message

    market_price = Stock(symbol).current_price()
    bought_shares = shares_owned(symbol)
    fee = read_data().get("fee_per_trade", 0.0)

    # If there is more shares sold then you have or if its 0, it won't run
    if shares > bought_shares:
        return False, 'Error: Cannot sell more stocks than owned'

    place_trade(symbol, -1 * shares, market_price)
    # Updates the cash value
    update_balance(shares * market_price - fee)
    return True, ''


# --- Calculations ---
# ----------------------------------------------------------------------------------------------------------


# Gives a main function for cost basis, shares owned and realized pnl as they do around the same things
def replay_symbol(symbol):
    rows = transactions(symbol)
    shares_left = 0
    cost_left = 0
    realized = 0

    for row in rows:
        shares = int(row['shares'])
        price = float(row['price'])
        trade_type = row['type'].lower()

        # If it is buy, it updates the shares and cost left
        if trade_type == 'buy':
            shares_left += shares
            cost_left += shares * price

        # If it is a sell, it gets the average cost and puts it in the realized value
        # Then it subtracts the cost left and shares left buy the amount sold
        elif trade_type == 'sell':
            shares = abs(shares)
            if shares_left == 0:
                continue

            avg_cost = cost_left / shares_left
            realized += (price - avg_cost) * shares
            cost_left -= avg_cost * shares
            shares_left -= shares

    return {
        "shares_left": shares_left,
        "cost_left": round(cost_left, 2),
        "realized_pnl": round(realized, 2)
    }


# Sees how many shares there are
def shares_owned(symbol):
    return replay_symbol(symbol)['shares_left']


# Gets the cost still invested
def cost_basis(symbol):
    return replay_symbol(symbol)['cost_left']


# Gets the position with the current market price
def position(symbol):
    if shares_owned(symbol) == 0:
        return 0
    return round(shares_owned(symbol) * Stock(symbol).current_price(), 2)


# Sum of all money ever spent buying a stock, ignoring sells
def total_invested(symbol):
    data = transactions(symbol)
    total = 0
    for i in data:
        if i['type'] == 'buy':
            total += int(i['shares']) * float(i['price'])
    return total


def total_invested_portfolio():
    return sum([total_invested(i) for i in all_symbols(owned=False)])


# --- PnL ---
# ----------------------------------------------------------------------------------------------------------


# Gets the difference between the current value and the past value, and is unrealized.
# This means that it is the pnl that is still invested and not turned into cash
def unrealized_pnl(symbol):
    if shares_owned(symbol) == 0:
        return 0
    return round(position(symbol) - cost_basis(symbol), 2)


# Gets the profit and loss of the whole portfolio, and is unrealized
def portfolio_pnl_unrealized():
    symbols = all_symbols()
    total = 0
    for i in symbols:
        total += unrealized_pnl(i)
    return round(total, 2)


# Gets the realized pnl for each stock
def realized_pnl(symbol):
    return replay_symbol(symbol)['realized_pnl']


# Gets the total pnl of a company you bought
def total_pnl(symbol):
    return unrealized_pnl(symbol) + realized_pnl(symbol)


# Gets the pnl from the stocks sold(realized) and the investment(unrealized)
def total_pnl_portfolio():
    return round(balance() + portfolio_value() - read_data()['starting_cash'], 2)


# --- ROI ---
# ----------------------------------------------------------------------------------------------------------

# Get the rate of investment, which measures the financial profit and loss by dividing the pnl by the original cost
def roi(symbol):
    ti = total_invested(symbol)
    if ti == 0:
        return 0
    return round(total_pnl(symbol) / ti * 100, 2)


# Gets the roi of the whole portfolio
def roi_portfolio():
    ti = total_invested_portfolio()
    if ti == 0:
        return 0
    return round(total_pnl_portfolio() / ti * 100, 2)


# Gives the performance and return vs starting cash
def roi_account():
    starting = read_data()['starting_cash']
    if starting == 0:
        return 0
    return round(total_pnl_portfolio() / starting * 100, 2)


# --- Portfolio ---
# ----------------------------------------------------------------------------------------------------------


# Gets the original price for the whole portfolio
def cost_basis_portfolio():
    return sum([cost_basis(i) for i in all_symbols()])


# Gets the current value of the portfolio
def portfolio_value():
    total = 0

    # Goes through all owned symbols and adds up their current market value
    for i in all_symbols():
        shares = shares_owned(i)
        total += shares * Stock(i).current_price()

    return round(total, 2)


# Gets all the symbols in the CSV and gets the ones that are owned depending on preference
def all_symbols(owned=True):
    data = all_transactions()
    symbols = set()
    for i in data:
        symbols.add(i['symbol'])

    if not owned:
        return list(symbols)

    return [i for i in symbols if shares_owned(i) > 0]


# Sees if the symbol exists in the transactions file
def find_symbol_exists(symbol):
    return symbol in all_symbols(owned=False)


# Gives a summary of that stock if specified, or it will give it for the whole portfolio for each stock
def summary(symbol=''):
    if symbol == '':
        info = []
        for i in all_symbols():
            info.append({
                "symbol": i,
                "shares": shares_owned(i),
                "position": position(i),
                "cost_basis": cost_basis(i),
                "unrealized_pnl": unrealized_pnl(i),
                "realized_pnl": realized_pnl(i),
                "total_pnl": total_pnl(i),
                "roi": roi(i)
            })
        return info
    else:
        symbol = symbol.strip().upper()
        if find_symbol_exists(symbol):
            return {
                "symbol": symbol,
                "shares": shares_owned(symbol),
                "position": position(symbol),
                "cost_basis": cost_basis(symbol),
                "unrealized_pnl": unrealized_pnl(symbol),
                "realized_pnl": realized_pnl(symbol),
                "total_pnl": total_pnl(symbol),
                "roi": roi(symbol)
            }


# Gives the stats of the whole portfolio
def portfolio_stats():
    return {
        "cash": balance(),
        "holdings_value": portfolio_value(),
        "total_value": round(balance() + portfolio_value(), 2),
        "total_pnl": total_pnl_portfolio(),
        "roi_portfolio": roi_portfolio(),
        "roi_account": roi_account()
    }
