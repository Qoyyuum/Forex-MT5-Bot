import MetaTrader5 as mt5
import config
import pandas as pd
import datetime
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print(f"Metatrader5 package author: {mt5.__author__}")
print(f"Metatrader5 package version: {mt5.__version__}")

# Date 10 days ago
utc_from=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)


def start():
    # Grab account info from config.py file
    ACCOUNT=getattr(config, "ACCOUNT", 25115284)
    SERVER=getattr(config, "SERVER", "MetaQuotes-Demo")
    PASSWORD=getattr(config, "PASSWORD", "4zatlbqx")
    # establish MetaTrader 5 connection to a specified trading account
    if not mt5.initialize(
        login=ACCOUNT,
        server=SERVER,
        password=PASSWORD,
    ):
        print(f"initialize() failed, error code ={mt5.last_error()}")
        # shut down connection to the MetaTrader 5 terminal
        exit()

    # display data on connection status, server name and trading account
    print(mt5.terminal_info())
    # display data on MetaTrader 5 version
    print(mt5.version())

    # display account info
    print("Account Info")
    account_info_dict=mt5.account_info()._asdict()

    print(f"Total of Orders: {mt5.orders_total}")
    # for prop in account_info_dict:
    #     print(f" {prop}={account_info_dict[prop]}")

    infoDataFrame(account_info_dict,c=['property', 'value'])
    
    # List of pairs to get
    # pairs = "*USD*,*EUR*,*JPY*,*SGD*,*GBP*,*CAD*"
    # getSymbols(pairs)
    
    # Get a symbol's info
    pairs = [
        "EURJPY",
        # "USDCAD"
        ]
    for p in pairs:
        getSymbolInfo(p)
        # copyRates(p)
        # copyAllTicks(p)
    exit()

def getSymbols(search):
    symbols=mt5.symbols_get(group=search)
    if symbols>0:
        print(f"Total symbols={symbols}")
    else:
        print("Symbols not found")

def getSymbolInfo(pair):
    # Attempt to enable the display of the selected pair symbol in MarketWatch
    selected = mt5.symbol_select(pair,True)
    if not selected:
        print(f"Failed to select {pair}")
        exit()

    # Display symbol info data
    symbol_info = mt5.symbol_info(pair)
    if symbol_info!=None:
        print("Showing Symbol's Info:\n")
        # for prop in symbol_info._asdict():
        #     print(f"    {prop}={symbol_info._asdict()[prop]}")

        # convert the dictionary into DataFrame and print
        symbol_info_dict = symbol_info._asdict()
        # df=pd.DataFrame(list(symbol_info_dict.items()),columns=['property','value'])
        # print(df)
        infoDataFrame(symbol_info_dict,c=['property', 'value'])

    print(f"!!!!!!!!!{pair} LAST TICK!!!!!!!!!!!!!")
    print(mt5.symbol_info_tick(pair))
    
def infoDataFrame(l, c):
    """
    To get symbol's info into a dataframe.

    :params l for list of items, usually a dictionary
    :params c for columns, to display in the dataframe. Expects an array of column names.
    :returns Nothing but print the value in console
    """
    df=pd.DataFrame(list(l.items()),columns=c)
    print(df)

def copyRates(pair, timeframe=mt5.TIMEFRAME_M1, from_date=utc_from, count=10):
    """
    Gets the historical symbol's data.

    :params pair for which valid symbol
    :params timeframe for which timeframe 
    :params from_date to collect from when until today
    :params count for how many bars to collect.
    :returns as a numpy array with named time, open, high, low, close, tick_volume, spread, and real_volume columns. None if error.

    NB: count of bars is dependant on the "Max. bars in chart" parameter in the MT5 terminal.
    """
    # (Do I just want 1 minute only?)
    
    # Set up for displaying the data in a proper tabular form
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1500)
    
    rates = mt5.copy_rates_from(pair, timeframe, from_date, 10)
    rates_frame = pd.DataFrame(rates)
    rates_frame['time']=pd.to_datetime(rates_frame['time'], unit='s')
    print(f"\nDisplaying Rates for {pair}")
    print(rates_frame)

def copyAllTicks(pair, from_date=utc_from, count=10, flag="mt5.COPY_TICKS_ALL"):
    """
    Gets the tick info historical symbol's data.

    :params pair for which valid symbol
    :params from_date to collect from when until today
    :params count for how many bars to collect.
    :params flag to indicate 
    :returns as a numpy array with named time, open, high, low, close, tick_volume, spread, and real_volume columns. None if error.

    NB: count of bars is dependant on the "Max. bars in chart" parameter in the MT5 terminal.
    """
    # (Do I just want 1 minute only?)
    
    # Set up for displaying the data in a proper tabular form
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1500)
    
    ticks = mt5.copy_ticks_from(pair, from_date, count, flag)
    ticks_frame = pd.DataFrame(ticks)
    ticks_frame['time']=pd.to_datetime(ticks_frame['time'], unit='s')
    print(f"\nDisplaying Ticks for {pair}")
    print(ticks_frame)


def buy(pair):
    """
    Check if the order request is a valid request before attempting to send the order through.
    Parameters are in kwargs which accepts a JSON request.

    E.g.
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": 1.0,
        "type": mt5.ORDER_TYPE_BUY,
        "price": mt5.symbol_info_tick(symbol).ask,
        "sl": mt5.symbol_info_tick(symbol).ask-100*point,
        "tp": mt5.symbol_info_tick(symbol).ask+100*point,
        "deviation": 10,
        "magic": 234000,
        "comment": "python script",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    """
    point = mt5.symbol_info(pair).point
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pair,
        "volume": 1.0,
        "type": mt5.ORDER_TYPE_BUY,
        "price": mt5.symbol_info_tick(symbol).ask,
        "sl": mt5.symbol_info_tick(symbol).ask-100*point,
        "tp": mt5.symbol_info_tick(symbol).ask+100*point,
        "deviation": 10,
        "magic": 234000,
        "comment": "Test script",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    print(f"Check: {mt5.order_check(request)}")

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"Result: {result}")
    else:
        print(f"Order send failed: {result.retcode}")


    



def exit():
    mt5.shutdown()
    quit()

if __name__ == "__main__":
    start()