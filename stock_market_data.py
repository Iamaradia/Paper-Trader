import yfinance as yf
import time
import pandas as pd
import matplotlib.pyplot as plt

# Example code to better understand, real functioning code is below
# Gets the data needed and makes a ticker object
symbol = 'AAPL'
ticker = yf.Ticker(symbol)
# How far in time you need to go
# Possible: "1d", "5d", "1mo", "6mo", "1y", "5y", "max"
period = '5d'
# How spaced out each point should be i.e. how granular it is
# Possible: "1m","2m","5m","15m","30m","60m","1d","1wk","1mo"
interval = '30m'


# Function for when importing
def data_frame_with_ticker(symbol, period, interval):
    return yf.download(symbol, period=period, interval=interval, progress=False)


df = data_frame_with_ticker(symbol, period, interval)
fig, ax1 = plt.subplots()

ax1.plot(df.index, df["Close"], label="Close")
#ax1.plot(df.index, df["High"], label="High")
#ax1.plot(df.index, df["Low"], label="Low")
#ax1.plot(df.index, df["Open"], label="Open")


ax1.set_ylabel("Price")

plt.show()
df.to_csv('df.csv')

# Making a class for the stocks data
class Stock:

    def __init__(self, ticker, period, interval):
        # Gets the data needed and makes a ticker object
        self.symbol = ticker
        self.ticker = yf.Ticker(self.symbol)
        # How far in time you need to go
        # Possible: "1d", "5d", "1mo", "6mo", "1y", "5y", "max"
        self.period = period
        # How spaced out each point should be i.e. how granular it is
        # Possible: "1m","2m","5m","15m","30m","60m","1d","1wk","1mo"
        self.interval = interval

    # When you need just a data frame
    def data_frame_with_ticker(self):
        return yf.download(self.symbol, period=self.period, interval=self.interval, progress=False)

    def output_graph(self):
        df = yf.download(self.symbol, period=self.period, interval=self.interval, progress=False)

