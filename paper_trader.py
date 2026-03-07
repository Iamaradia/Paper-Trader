from stock_market_data import *
from pathlib import Path
import csv
from datetime import datetime

# Initializes the file and if not there, makes a new one
data = Path("paper_data.csv")

if not data.exists():
    with open(data, 'w', newline='') as f:
        writer = csv.writer(f)
        # These are the headers
        writer.writerow(['symbol', 'shares', 'price', 'time'])

# Gives the time now in the following format 2026-03-05 19:41:28
time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Gives all the other information needed
# TEST DATA
stock = Stock('TSLA')
price = stock.current_price()
shares = 2

"""with open(data, 'a', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(row_maker(stock.symbol, shares, price, time))"""


# Gives all the rows in a generator function
def read_all():
    with open(data, 'r') as f:
        reader = csv.reader(f)
        for i in reader:
            yield i


# Faster to write rows
def row_maker(symbol, shares, market_price, time):
    with open(data, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([symbol, shares, market_price, time])


# Sort each of the rows by their header
def dict_sort(rows):
    header = rows[0]
    data = rows[1:]
    return [dict(zip(header, row)) for row in data]


# To get the postion of each share you own by searching the files and adding or subtracting the shares value to get the price
def cost_basis(symbol):
    data = dict_sort(list(read_all()))
    valid_indices = []
    for i in range(len(data)):
        if data[i]['symbol'] == symbol:
            valid_indices.append(i)
    cost_basis = 0
    for i in valid_indices:
        shares = int(data[i]['shares'])
        price = float(data[i]['price'])
        cost_basis += shares * price
    return cost_basis


row_maker(stock.symbol, shares, price, time)
print(cost_basis(stock.symbol))
