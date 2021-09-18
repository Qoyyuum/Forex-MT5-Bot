import MetaTrader5 as mt5
import config
import pandas as pd
import datetime
import logging
import pytz
from torch.utils.data import Dataset

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# print(f"Metatrader5 package author: {mt5.__author__}")
# print(f"Metatrader5 package version: {mt5.__version__}")


class Client:
    def __init__(self, server, account, password):
        self.account=getattr(config, "ACCOUNT", 25115284)
        self.server=getattr(config, "SERVER", "MetaQuotes-Demo")
        self.password=getattr(config, "PASSWORD", "4zatlbqx")
        self.pairs=getattr(config, "PAIRS", "USDJPY")
        self.timezone = pytz.timezone(getattr(config, "TIMEZONE", "Etc/UTC"))
        # Date 10 days ago
        # utc_from=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365)
        self.utc_from = datetime.datetime(2021,1,1,tzinfo=self.timezone)
        self.utc_to = datetime.datetime(2021,1,28,tzinfo=self.timezone)

        # establish MetaTrader 5 connection to a specified trading account
        if not mt5.initialize(
            login=self.account,
            server=self.server,
            password=self.password,
        ):
            print(f"initialize() failed, error code ={mt5.last_error()}")
            # shut down connection to the MetaTrader 5 terminal
            self.exit()

    def exit(self):
        mt5.shutdown()
        # quit()

    def testCopyRates(self):
        """
        Test Copying Rate and save it into a file to manipulate with.
        https://www.mql5.com/en/docs/integration/python_metatrader5/mt5copyratesfrompos_py
        """
        with open("EURJPY-rates.json", "w") as f:
            rates = mt5.copy_rates_from_pos("EURJPY", mt5.TIMEFRAME_M1, 0, 100)
            # if mt5.last_error()
            f.write(str(rates))
            # print(f"RATES: {rates}")
            print("Finished rates!")

    def getSymbols(self,search):
        symbols=mt5.symbols_get(group=search)
        print(f"Searched pairs:\n{[s.name for s in symbols]}")

    def getSymbolInfo(self,pair):
        # Attempt to enable the display of the selected pair symbol in MarketWatch
        selected = mt5.symbol_select(pair,True)
        if not selected:
            print(f"Failed to select {pair}")
            exit()

        # Display symbol info data
        symbol_info = mt5.symbol_info(pair)
        if symbol_info!=None:
            print("Showing Symbol's Info:\n")

            symbol_info_dict = symbol_info._asdict()
            self.infoDataFrame(symbol_info_dict,c=['property', 'value'])

        print(f"!!!!!!!!!{pair} LAST TICK!!!!!!!!!!!!!")
        print(mt5.symbol_info_tick(pair))
        
    def infoDataFrame(self,l, c):
        """
        To get symbol's info into a dataframe.

        :params l for list of items, usually a dictionary
        :params c for columns, to display in the dataframe. Expects an array of column names.
        :returns Nothing but print the value in console
        """
        df=pd.DataFrame(list(l.items()),columns=c)
        print(df)

    def copyRates(self, pair, from_date, timeframe=mt5.TIMEFRAME_M1, count=1000):
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
        print(f"Copying rates from : {pair} at {timeframe} starting from {from_date} and will collect {count} bars")
        rates = mt5.copy_rates_from(pair, timeframe, from_date, count)
        rates_frame = pd.DataFrame(rates)
        print("DataFrame :")
        print(f"{rates_frame}")
        rates_frame['time']=pd.to_datetime(rates_frame['time'], unit='s')
        print(f"\nDisplaying Rates for {pair}")
        print(rates_frame)
        return rates

    def copyAllTicks(self, pair, from_date, count=10, flag="mt5.COPY_TICKS_ALL"):
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


    def buy(self, pair, lots) -> bool:
        """
        First checks if the order request is valid and then pass in the request object
        and execute the order for a buy.

        :params pair - string - symbol to place a buy order
        :params lots - float - value for amount of lots
        :return boolean

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
        price = mt5.symbol_info_tick(pair).ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pair,
            "volume": lots,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "sl": price-100*point,
            "tp": price+100*point,
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
            return True
        else:
            print("!!!!!!!!!!!!ORDER_SEND FAILED!!!!!!!!!")
            print(f"Error: {result.retcode}")
            print(f"Result: {result}")
            return False

    def sell(self, pair, lots) -> bool:
        """
        First checks if the order request is valid and then pass in the request object
        and execute the order for a buy.

        :params pair - string - symbol to place a buy order
        :params lots - float - value for amount of lots
        :return boolean

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
        price = mt5.symbol_info_tick(pair).ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pair,
            "volume": lots,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "sl": price-100*point,
            "tp": price+100*point,
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
            return True
        else:
            print(f"Order send failed: {result.retcode}")
            return False

class ForexDataset(Dataset):
    def __init__(self, transform=None, target_transform=None):
        self.rates = Client(account=config.ACCOUNT, server=config.SERVER, password=config.PASSWORD).copyRates()
        self.transform = transform
        self.target_transform = target_transform
    
    def __len__(self):
        return len(self.rates)

    def __getitem__(self, idx):
        label = self.rates.iloc[idx]
        if self.transform:
            price = self.transform(self.rates)
        if self.target_transform:
            label = self.target_transform(label)
        return price, label
        

if __name__ == "__main__":
    c = Client(account=config.ACCOUNT, server=config.SERVER, password=config.PASSWORD)
    c.testCopyRates()

    from torch.utils.data import DataLoader

    train_dataloader = DataLoader(training_data, batch_size=64, shuffle=False)
    test_dataloader = DataLoader(test_data, batch_size=64, shuffle=False)