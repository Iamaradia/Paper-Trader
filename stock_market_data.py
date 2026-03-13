import yfinance as yf
import time
import requests



# Making a class for the stocks transactions
class Stock:

    def __init__(self, ticker, period='30m', interval='1d'):
        # Gets the transactions needed and makes a ticker object
        self.symbol = ticker
        self.ticker = yf.Ticker(self.symbol)
        # How far in time you need to go
        # Possible: "1d", "5d", "1mo", "6mo", "1y", "5y", "max"
        self.period = period
        # How spaced out each point should be i.e. how granular it is
        # Possible: "1m","2m","5m","15m","30m","60m","1d","1wk","1mo"
        self.interval = interval

    # When you need just a transactions frame
    def data_frame_with_ticker(self):
        return yf.download(self.symbol, period=self.period, interval=self.interval, progress=False)

    # Gives an unformatted graph
    def output_graph(self):
        df = yf.download(self.symbol, period=self.period, interval=self.interval, progress=False)

    # Gives the current price when it was called
    # Can be delayed
    def current_price(self):
        info = self.ticker.fast_info
        price = info.get("last_price") or info.get("regularMarketPrice")

        if price is None:
            hist = self.ticker.history(period="1d")
            price = hist["Close"].iloc[-1]

        return round(price, 2)

    def moving_average(self, window=4):
        df = self.data_frame_with_ticker()
        return df["Close"].rolling(window).mean().dropna()


"""apple = Stock(symbol, period, interval)
print(apple.moving_average())
apple.period = '1d'
print(apple.moving_average())"""

# Gets the first search result in case they don't know the ticker
def search(query):
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}"
    # Makes it seem like it is an user instead of a script
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers)
    data = r.json()

    if not data["quotes"]:
        return []

    symbols = []

    for q in data["quotes"]:
        symbols.append(q["symbol"])

    return symbols


