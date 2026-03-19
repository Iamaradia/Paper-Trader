from stock_market_data import Stock, search
import paper_trader as pt
import streamlit as st
import pandas as pd
import yfinance as yf
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Paper Trader", layout="wide", page_icon="📈")

# ------------------------------ Session State ------------------------------

# Stores the ticker the user is currently viewing
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = ""

# Stores whatever is in the search box
if "search_input" not in st.session_state:
    st.session_state.search_input = ""

# A flag to safely clear the input box
if "clear_search" not in st.session_state:
    st.session_state.clear_search = False

# Stores the period that the user is using
if "selected_period" not in st.session_state:
    st.session_state.selected_period = "1D"

if "confirm_buy" not in st.session_state:
    st.session_state.confirm_buy = False

if "confirm_sell" not in st.session_state:
    st.session_state.confirm_sell = False


# ------------------------------ Helpers ------------------------------

# Gets the company name and current price for one ticker
# Cached for 60 seconds, so it does not keep hitting the API on every rerun
@st.cache_data(ttl=60, show_spinner=False)
def enrich(ticker):
    stock = yf.Ticker(ticker)
    name = stock.info.get("longName") or stock.info.get("shortName") or ticker
    price = Stock(ticker).current_price()
    return {"ticker": ticker, "name": name, "price": price}


@st.cache_data(ttl=60, show_spinner=False)
def fetch_history(ticker, period, interval):
    df = Stock(ticker, period=period, interval=interval).data_frame_with_ticker()
    df.index = pd.to_datetime(df.index)
    return df


# Gets the ROI of a stock in that time period
def stock_roi(ticker):
    periods = {
        "1D": ("1d", "5m"),
        "1W": ("5d", "30m"),
        "1M": ("1mo", "1d"),
        "6M": ("6mo", "1d"),
        "1Y": ("1y", "1d"),
        "5Y": ("5y", "1wk")
    }

    period, interval = periods[st.session_state.selected_period]
    df = fetch_history(ticker, period, interval)

    if df.empty:
        return None

    close = df["Close"].squeeze()

    if not hasattr(close, "__len__"):
        close = pd.Series([close])

    if len(close) < 2:
        return None

    start_price = close.iloc[0]
    end_price = close.iloc[-1]

    if start_price == 0:
        return None

    roi_percent = ((end_price - start_price) / start_price) * 100
    return roi_percent


# ------------------------------ Pages ------------------------------


# This is the home page
def dashboard():
    st.title("Dashboard")

    stats = pt.portfolio_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", f"${stats['total_value']:,.2f}")
    c2.metric("Cash", f"${stats['cash']:,.2f}")
    c3.metric("Holdings", f"${stats['holdings_value']:,.2f}")
    c4.metric("Total P&L", f"${stats['total_pnl']:,.2f}",
              delta=f"{stats['roi_account']:.2f}% ROI")

    summary = pt.summary()

    if summary:
        labels = [s["symbol"] for s in summary]
        values = [s["position"] for s in summary]

        fig = px.pie(names=labels, values=values, hole=0.5)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=True,
            margin=dict(l=0, r=0, t=0, b=0),
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.divider()
    st.subheader('Owned Stocks')

    raw_owned = pt.all_symbols()
    owned = []
    for i in raw_owned:
        try:
            owned.append(enrich(i))
        except Exception:
            continue

    if not owned:
        st.badge("Start buying stocks!.", icon=':material/search_off:', color="red", width='stretch')

    if owned:
        with st.container(border=True):
            for i, r in enumerate(owned):
                ticker_area, name_area, amount_area, price_area, button_area = st.columns([1, 2.2, 1, 1, 0.5])

                with ticker_area:
                    st.markdown(
                        f"<div style='font-weight:600; margin:0; padding-top:8px'>{r['ticker']}</div>",
                        unsafe_allow_html=True
                    )
                with name_area:
                    st.markdown(
                        f"<div style='color:gray; font-size:12px; padding-top:10px'>{r['name']}</div>",
                        unsafe_allow_html=True
                    )

                with amount_area:
                    st.markdown(
                        f"<div style='color:gray; font-size:14px; padding-top:10px'>Amount Owned: {pt.shares_owned(r['ticker'])}</div>",
                        unsafe_allow_html=True
                    )

                with price_area:
                    st.markdown(
                        f"<div style='text-align:right; padding-top:8px'>${r['price']:.2f}</div>",
                        unsafe_allow_html=True
                    )
                with button_area:
                    # Each button gets a unique key to avoid duplicate key errors
                    if st.button("→", key=f"{r['ticker']}_{i}", use_container_width=True):
                        st.session_state.active_ticker = r["ticker"]
                        st.switch_page(explore_page)

                # Divider between rows but not after the last one
                if i < len(owned) - 1:
                    st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)


# Just the search input and results list
def search_bar():
    st.markdown("""
    <style>
    div[data-testid="stMarkdownContainer"] p { margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

    # Clears the search input before making text_input
    if st.session_state.clear_search:
        st.session_state.search_input = ""
        st.session_state.clear_search = False

    # Wide area for typing, small area for the search button
    col1, col2 = st.columns([20, 1])

    with col1:
        ticker_input = st.text_input(
            "",
            placeholder="Search ticker or name (AAPL, Tesla...)",
            label_visibility="collapsed",
            key="search_input"
        ).strip()

    with col2:
        search_clicked = st.button(":material/search:")

    # If they click the search icon, open that ticker directly
    if search_clicked and ticker_input:
        st.session_state.active_ticker = ticker_input.upper()
        st.session_state.clear_search = True
        st.rerun()

    # Only show results when something is typed
    if ticker_input:
        raw_results = search(ticker_input)[:5]

        # Enrich each ticker string with name and price and guard it in case it can't find anything
        results = []

        for r in raw_results:
            try:
                results.append(enrich(r))
            except Exception:
                continue

        if not results:
            st.badge("Sorry, couldn't find anything.", icon=':material/search_off:', color="red", width='stretch')

        if results:
            with st.container(border=True):
                for i, r in enumerate(results):
                    ticker_area, name_area, price_area, button_area = st.columns([1, 2.2, 1, 0.5])

                    with ticker_area:
                        st.markdown(
                            f"<div style='font-weight:600; margin:0; padding-top:8px'>{r['ticker']}</div>",
                            unsafe_allow_html=True
                        )
                    with name_area:
                        st.markdown(
                            f"<div style='color:gray; font-size:12px; padding-top:10px'>{r['name']}</div>",
                            unsafe_allow_html=True
                        )
                    with price_area:
                        st.markdown(
                            f"<div style='text-align:right; padding-top:8px'>${r['price']:.2f}</div>",
                            unsafe_allow_html=True
                        )
                    with button_area:
                        # Each button gets a unique key to avoid duplicate key errors
                        if st.button("→", key=f"{r['ticker']}_{i}", use_container_width=True):
                            st.session_state.active_ticker = r["ticker"]
                            st.session_state.clear_search = True
                            st.rerun()

                    # Divider between rows but not after the last one
                    if i < len(results) - 1:
                        st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)


# The stock detail view — shown when a ticker is selected
def stock_info(active_ticker):
    # Back button returns user to search
    if st.button("← Back to Search"):
        st.session_state.active_ticker = ""
        st.session_state.clear_search = True
        st.rerun()

    # Refreshes price every 60 seconds automatically
    st_autorefresh(interval=60_000, key="price_refresh")

    try:
        stock = yf.Ticker(active_ticker)
        info = stock.info
        name = info.get("longName") or info.get("shortName") or active_ticker
        price = Stock(active_ticker).current_price()
    except Exception as e:
        st.error(f"Could not load stock data: {e}")
        return

    roi = stock_roi(active_ticker)
    st.subheader(active_ticker)

    if roi is not None:
        if roi >= 0:
            st.badge(f"+{roi:.2f}%", color="green", icon=':material/arrow_upward:')
        else:
            st.badge(f"{roi:.2f}%", color="red", icon=':material/arrow_downward:')

    st.caption(name)

    try:
        price = Stock(active_ticker).current_price()
        st.metric("Current Price", f"${price:.2f}")

        stock_chart(active_ticker)
        buy_and_sell(active_ticker)

    except Exception as e:
        st.error(f"Could not load stock data: {e}")


# The main explore page — decides whether to show search or stock info
def explore():
    st.title("Explore")

    active_ticker = st.session_state.get("active_ticker", "")

    if active_ticker:
        # A ticker is selected — show the stock detail view
        stock_info(active_ticker)
    else:
        # Nothing selected — show the search bar
        search_bar()


# Shows all the transactions in a dataframe they can cleanly see
def transactions_page():
    st.title("Transactions")
    st.caption('Disclaimer: All of those times are in PT because I did not want to ask people their location')
    df = pd.read_csv(pt.transactions_file)

    if df.empty:
        st.info("No transactions yet — head to Explore to make your first trade.")
        return

    # Filter by ticker
    tickers = ["All"] + sorted(pt.all_symbols(owned=False))
    selected = st.selectbox("Filter by ticker", tickers, label_visibility="collapsed")

    if selected != "All":
        df = df[df["symbol"] == selected]

    st.dataframe(df, use_container_width=True, hide_index=True, height='content')


# Fetches data and makes a plotly chart
def stock_chart(ticker):
    # Period selector
    periods = {"1D": ("1d", "5m"), "1W": ("5d", "30m"), "1M": ("1mo", "1d"),
               "6M": ("6mo", "1d"), "1Y": ("1y", "1d"), "5Y": ("5y", "1wk")}

    # CSS to make buttons transparent and underline the active one
    st.markdown("""
    <style>
    /* All period buttons */
    div[data-testid="stHorizontalBlock"] button {
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important;
        color: #888 !important;
        font-size: 0.85rem !important;
        padding: 4px 8px !important;
        transition: all 0.15s ease;
    }

    /* Active period button */
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {
        color: white !important;
        border-bottom: 2px solid white !important;
    }

    div[data-testid="stHorizontalBlock"] button:hover {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Render one button per period in a row
    cols = st.columns(len(periods))
    # Mark the active period so CSS can style it differently
    for col, label in zip(cols, periods.keys()):
        with col:
            is_active = label == st.session_state.selected_period
            if st.button(label, use_container_width=True,
                         key=f"period_{ticker}_{label}",
                         type="primary" if is_active else "secondary"):
                st.session_state.selected_period = label
                st.rerun()

    # Fetch data for the currently selected period
    period, interval = periods[st.session_state.selected_period]
    df = fetch_history(ticker, period, interval)

    # If no data, try falling back to the next shorter period
    if df.empty:
        fallback_order = ["1Y", "6M", "1M", "1W", "1D"]
        for fallback in fallback_order:
            period, interval = periods[fallback]
            df = fetch_history(ticker, period, interval)
            if not df.empty:
                st.caption(f"No {st.session_state.selected_period} data available — showing {fallback} instead.")
                break

    if df.empty:
        st.warning("No chart data available for this ticker.")
        return

    # Squeeze in case yfinance returns a DataFrame instead of a Series
    close = df["Close"].squeeze()

    # If squeeze collapsed it to a scalar, wrap it back into a Series
    if not hasattr(close, "__len__"):
        close = pd.Series([close])

    if len(close) < 2:
        return None

    # Green if price is up over the period, red if down
    is_up = close.iloc[-1] >= close.iloc[0]
    color = "#00c076" if is_up else "#ff5252"
    fill = "rgba(0,192,118,0.1)" if is_up else "rgba(255,82,82,0.1)"

    # Creates an empty plotly figure (lol)
    fig = go.Figure()
    # Padding above and below the price range in the chart
    padding = (close.max() - close.min()) * 0.1 or 1.0

    # Main price line with gradient fill underneath
    fig.add_trace(go.Scatter(
        x=df.index,
        y=close,
        mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=fill,
        hovertemplate="$%{y:.2f}<extra></extra>",
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",  # transparent so it matches your app theme
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=350,
        xaxis=dict(
            showgrid=False,
            showline=False,
            zeroline=False,
            tickfont=dict(color="#888"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            showline=False,
            zeroline=False,
            tickfont=dict(color="#888"),
            tickprefix="$",
            side="right",
            range=[close.min() - padding, close.max() + padding]
        ),
        hovermode="x unified",
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# Handles the buy and sell functions
def buy_and_sell(ticker):
    st.divider()
    st.markdown("#### Trade")

    # The values to show for each stock below the chart
    bal = pt.balance()
    owned = pt.shares_owned(ticker)
    cost_basis = pt.cost_basis(ticker)
    total_invested = pt.total_invested(ticker)
    position = pt.position(ticker)
    roi = pt.roi(ticker)
    pnl = pt.total_pnl(ticker)

    stat1, stat2, stat3, stat4, stat5, stat6 = st.columns(6)
    stat1.metric("Cash Balance", f"${bal:,.2f}")
    stat2.metric("Shares Owned", owned)
    stat3.metric("Total Invested", f"${total_invested:,.2f}")
    stat4.metric("Invested Now", f"${cost_basis:,.2f}")
    stat5.metric("Position", f"${position:,.2f}", f"{roi:+,.2f}%")
    # Fixes $-xx.xx to -$xx.xx
    stat6.metric("Total P&L", "—" if pnl is None else (f"${pnl:,.2f}" if pnl >= 0 else f"-${abs(pnl):,.2f}"))

    col1, col2 = st.columns(2)

    with col1:
        buy_shares = st.number_input("Shares to buy", min_value=1, step=1, key="buy_input")

        # Show estimated total cost before confirming
        price = Stock(ticker).current_price()
        total_cost = price * buy_shares
        st.caption(f"Total cost: ${total_cost:,.2f}")

        if not st.session_state.confirm_buy:
            if st.button("Buy", use_container_width=True):
                st.session_state.confirm_buy = True
                st.rerun()
        else:
            st.warning(f"Buy {buy_shares} shares of {ticker} for ${total_cost:,.2f}?")
            yes, no = st.columns(2)
            with yes:
                if st.button("✅ Yes", use_container_width=True, key="confirm_yes"):
                    success, message = pt.buy(ticker, buy_shares)
                    if success:
                        st.success(f"Bought {buy_shares} shares of {ticker}")
                        fetch_history.clear()
                        enrich.clear()
                        st.session_state.confirm_buy = False
                        st.rerun()
                    else:
                        st.error(message)
                        st.session_state.confirm_buy = False
            with no:
                if st.button("❌ No", use_container_width=True, key="confirm_no"):
                    st.session_state.confirm_buy = False
                    st.rerun()

    with col2:
        sell_shares = st.number_input("Shares to Sell", min_value=1, step=1, key="sell_input")

        price = Stock(ticker).current_price()
        total_return = price * sell_shares
        st.caption(f"Total return: ${total_return:,.2f}")

        if not st.session_state.confirm_sell:  # ← was confirm_buy
            if st.button("Sell", use_container_width=True):
                st.session_state.confirm_sell = True
                st.rerun()
        else:
            st.warning(f"Sell {sell_shares} shares of {ticker} for ${total_return:,.2f}?")
            yes, no = st.columns(2)
            with yes:
                if st.button("✅ Yes", use_container_width=True, key="sell_confirm_yes"):  # ← unique key
                    success, message = pt.sell(ticker, sell_shares)  # ← was pt.buy, buy_shares
                    if success:
                        st.success(f"Sold {sell_shares} shares of {ticker}")
                        fetch_history.clear()
                        enrich.clear()
                        st.session_state.confirm_sell = False
                        st.rerun()
                    else:
                        st.error(message)
                        st.session_state.confirm_sell = False
            with no:
                if st.button("❌ No", use_container_width=True, key="sell_confirm_no"):  # ← unique key
                    st.session_state.confirm_sell = False
                    st.rerun()


# ------------------------------ App Navigation ------------------------------

explore_page = st.Page(explore, title="Explore", icon=":material/search:")
pg = [
    st.Page(dashboard, title="Dashboard", icon="📊"),
    explore_page,
    st.Page(transactions_page, title="Transactions", icon="📋"),
]

pages = st.navigation(pg, position="top")
pages.run()
