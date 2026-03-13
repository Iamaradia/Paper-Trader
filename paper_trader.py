from stock_market_data import Stock
from pathlib import Path
import csv
from datetime import datetime
import json

# Initializes the files and if not there, makes new ones
transactions = Path("paper_transactions.csv")
data_file = Path("paper_data.json")

if not transactions.exists():
    with open(transactions, 'w', newline='') as f:
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


# Gives all the rows in the log into a list and if there are empty lines, auto-cleans it
def read_transactions():
    rows = []
    original_rows = []

    # Reads all the rows, and if it is empty, it ignores it
    with open(transactions, 'r') as file:
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
        with open(transactions, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(rows)

    return rows


# Gets all the symbols in the CSV and gets the ones that are owned depending on preference
def all_symbols(owned=True):
    data = dict_sort(read_transactions())
    symbols = set()
    for i in data:
        symbols.add(i['symbol'])
    return [i for i in symbols if shares_owned(i) > 0] if owned else list(symbols)


# Sees if the symbol exists in the transactions file
def find_symbol_exists(symbol):
    return symbol in all_symbols()


# Sees how many shares there are
def shares_owned(symbol):
    if not find_symbol_exists(symbol):
        return 0
    data = dict_sort(read_transactions())
    total = 0
    for i in data:
        if i['symbol'] == symbol:
            total += int(i['shares'])
    return total


# Fills in the transactions and sends to CSV
def place_trade(symbol, shares, market_price):
    # Sees if the symbol is empty
    symbol = symbol.strip().upper()
    if symbol == "" or shares is None:
        return False



    # Opens the log file and writes the transaction
    with open(transactions, 'a', newline='') as file:
        writer = csv.writer(file)
        # Sees if it is a buy or a sell depending on the sign, or if it is none
        trade_type = "buy" if shares > 0 else "sell"
        # Gives the time now in the following format 2026-03-05 19:41:28
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([symbol, shares, market_price, time, trade_type])


# Sort each of the rows by their header
def dict_sort(rows):
    if not rows:
        return []

    header = rows[0]
    data = rows[1:]
    return [dict(zip(header, row)) for row in data]


# To get the cost basis of each share you own by searching the files
# and adding or subtracting the shares value you bought it for to get the price
def cost_basis(symbol):
    if shares_owned(symbol) == 0:
        return 0
    if not find_symbol_exists(symbol):
        return None
    data = dict_sort(read_transactions())

    total_shares = 0
    total_cost = 0

    for i in data:
        if i['symbol'] == symbol:
            shares = int(i['shares'])
            price = float(i['price'])
            if shares > 0:
                total_cost += shares * price
                total_shares += shares

    if total_shares == 0:
        return 0

    average = total_cost / total_shares
    return round(average*shares_owned(symbol), 2)


# Gets the position with the current market price
def position(symbol):
    if shares_owned(symbol) == 0:
        return 0
    return round(shares_owned(symbol) * Stock(symbol).current_price(), 2)


# Gets the difference between the current value and the past value
def pnl(symbol):
    if not find_symbol_exists(symbol):
        return 0
    if shares_owned(symbol) == 0:
        return 0
    return position(symbol) - cost_basis(symbol)


# Gets the profit and loss of the whole portfolio
def portfolio_pnl():
    symbols = all_symbols()
    total = 0
    for i in symbols:
        total += pnl(i)
    return round(total, 2)


# Gets the current value of the portfolio
def portfolio_value():
    data = dict_sort(read_transactions())
    value = 0
    cache = {}

    # Goes through all the rows to see if it cached. If it is, it will use that value, otherwise it will get it online
    for i in data:
        if i['symbol'] in cache:
            value += cache[i['symbol']] * int(i['shares'])
            continue
        cache.update({i['symbol']: Stock(i['symbol']).current_price()})
        value += cache[i['symbol']] * int(i['shares'])

    return round(value, 2)


# Gives the data in the JSON file
def read_data():
    if not data_file.exists():
        return {}
    with open(data_file, 'r') as file:
        return json.load(file)


# Get the cash balance
def balance():
    data = read_data()
    return data.get("cash", 0.0)


# Changes the json file by rewriting it
def write_data(data):
    with open(data_file, 'w') as file:
        json.dump(data, file, indent=4)


# Updates the cash balance
def update_balance(amount):
    data = read_data()
    data['cash'] += amount
    write_data(data)


# Handles the logic to buy stocks by check if valid and then placing trade and updating balance
def buy(symbol, shares):
    if not check_transaction(symbol, shares):
        return False

    market_price = Stock(symbol).current_price()
    fee = read_data().get("fee_per_trade", 0.0)

    # If you have less cash then the cost of the transaction, or if shares less than zero it won't run
    if balance() < shares * market_price + fee:
        return False

    place_trade(symbol, shares, market_price)
    # Updates the cash value, so it goes down by the cost
    update_balance(-(shares * market_price + fee))
    return True


# Handles the logic to sell stocks by checking if valid and then placing trade and updating balance
def sell(symbol, shares):
    if not check_transaction(symbol, shares):
        return False

    market_price = Stock(symbol).current_price()
    bought_shares = shares_owned(symbol)
    fee = read_data().get("fee_per_trade", 0.0)

    # If there is more shares sold then you have or if its 0, it won't run
    if shares > bought_shares:
        return False

    place_trade(symbol, -1 * shares, market_price)
    # Updates the cash value
    update_balance(shares * market_price - fee)
    return True

# Checks the symbols and shares in one place
def check_transaction(symbol, shares):
    if shares <= 0 or shares is None:
        return False

    if symbol == "":
        return False

    try:
        price = Stock(symbol).current_price()
    except:
        return False

    return True