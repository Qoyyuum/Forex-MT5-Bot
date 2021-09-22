import pandas as pd
from sklearn.model_selection import train_test_split
from datetime import datetime
import MetaTrader5 as mt5
import config
from dataclasses import dataclass
import numpy as np


@dataclass
class Client:
    account: int
    password: str
    server: str
    pair: str
    lot: float
    timeframe: np.ndarray

    def login(self):
        "Client login"
        if mt5.login(login=self.account, password=self.password, server=self.server):
            print("Logged in")
            return True
        else:
            print("Failed to login")
            return False

    def analyze_and_trade(self):
        """Analyze the past 100 rates and trade on the current open price"""
        rates = mt5.copy_rates_from_pos(self.pair, self.timeframe, 1, 100)
        while rates is None:
            rates = mt5.copy_rates_from_pos(self.pair, self.timeframe, 1, 100)

        df_data = pd.DataFrame(rates)
        df_x = df_data.drop(columns="close")
        df_y = df_data["close"]

        x_train, x_test, y_train, y_test = train_test_split(
            df_x, df_y, test_size=0.2, random_state=0
        )
        model = self.get_model_to_predict(x_train, y_train)
        # current_rate = mt5.copy_rates_from_pos(self.pair, self.timeframe, 0, 1)
        # current_df = pd.DataFrame(current_rate)
        # current_open_price = current_df.iloc[0]["open"]
        # to_predict = current_df.drop(columns="close")
        to_predict = self.get_current_rate_to_predict()
        self.y_predict = model.predict(to_predict)
        # print(
        #     f"y_predict for {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} at open price of {current_open_price} : {self.y_predict}"
        # )
        if current_open_price > float(self.y_predict[0]):
            print("Sell")
            self.order("sell")
        else:
            print("Buy")
            self.order("buy")

    def get_current_rate_to_predict(self):
        """
        Get the current rate and return it
        """
        current_rate = mt5.copy_rates_from_pos(self.pair, self.timeframe, 0, 1)
        current_df = pd.DataFrame(current_rate)
        current_open_price = current_df.iloc[0]["open"]
        return current_df.drop(columns="close")

    def get_model_to_predict(self, x_train, y_train):
        """
        Build a model to fit with the x and y training data set and fit.

        Returns the built and learned model
        """
        from sklearn.linear_model import LinearRegression

        return LinearRegression().fit(x_train, y_train)

    def order(self, signal):
        "Gets ASK price and place a ORDER_TYPE_BUY"
        symbol_info = mt5.symbol_info(self.pair)
        if symbol_info is None:
            print(f"{self.pair} not found, cannot call order_check()")
            mt5.shutdown()
            quit()

        if not symbol_info.visible:
            print(f"{self.pair} is not visible, trying to switch on")
            if not mt5.symbol_select(self.pair, True):
                print(f"symbol_select({self.pair}) failed, exit")
                mt5.shutdown()
                quit()
        # point = mt5.symbol_info(self.pair).point
        order_type, price = (
            (mt5.ORDER_TYPE_SELL, mt5.symbol_info_tick(self.pair).bid)
            if signal == "sell"
            else (mt5.ORDER_TYPE_BUY, mt5.symbol_info_tick(self.pair).ask)
        )
        self.raw_order(
            action=mt5.TRADE_ACTION_DEAL,
            symbol=self.pair,
            volume=self.lot,
            type=order_type,
            price=price,
            tp=float(self.y_predict[0]),
            deviation=20,
            magic=20210922,
            comment="my last shot",
            type_time=mt5.ORDER_TIME_GTC,
            type_filling=mt5.ORDER_FILLING_RETURN,
        )
        print(
            f"Order Sent : by {self.pair} {self.lot} lots at {price} with deviation 20 points"
        )

    def raw_order(self, **kwargs):
        result = mt5.order_send(kwargs)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Order Send Failed, RETCODE = {result.retcode}")
        else:
            print(f"Order send done. Result: {result}")
        # print(f"Opened position with POSITION_TICKET: {result.order}")
        return result


if __name__ == "__main__":
    if not mt5.initialize():
        print(f"MT5 Init failed, error code {mt5.last_error()}")
        quit()
    else:
        for p in config.PAIRS:
            c = Client(
                config.ACCOUNT,
                config.PASSWORD,
                config.SERVER,
                p,
                config.LOT_SIZE,
                config.TIMEFRAME,
            )
            if c.login():
                c.analyze_and_trade()
