import logging
import logging.config
from dataclasses import dataclass

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

import config

logging.config.fileConfig("logging.conf")

logger = logging.getLogger("app")
# if config.DEBUGMODE:
#     LOGFORMAT='%(asctime)s %(message)s'
#     logging.basicConfig(filename=config.LOGFILENAME, format=LOGFORMAT, encoding='utf-8', level=logging.DEBUG)


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
        if mt5.login(
            login=self.account, password=self.password, server=self.server
        ):
            logger.info(
                f"Logged in to {self.server} with account {self.account}"
            )
            return True
        else:
            logger.critical(
                f"Failed to login to {self.server} with account {self.account}"
            )
            return False

    def analyze_and_trade(self):
        """Analyze the past 100 rates and trade on the current open price"""
        rates = mt5.copy_rates_from_pos(self.pair, self.timeframe, 1, 100)
        logger.debug(f"Fetched rates for {self.pair} :\n{rates}")

        df_data = pd.DataFrame(rates)
        df_x = df_data.drop(columns="close")
        df_y = df_data["close"]

        x_train, x_test, y_train, y_test = train_test_split(
            df_x, df_y, test_size=0.2, random_state=0
        )
        logger.debug(f"x_train :\n{x_train}")
        logger.debug(f"x_test :\n{x_test}")
        logger.debug(f"y_train :\n{y_train}")
        logger.debug(f"y_test :\n{y_test}")
        model = self.get_model_to_predict(x_train, y_train)
        logger.debug(f"Trained Model:\n{model}")
        current_open_price, to_predict = self.get_current_rate_to_predict()
        self.y_predict = model.predict(to_predict)
        if current_open_price > float(self.y_predict[0]):
            logger.debug(
                f"Sell at {current_open_price} with predicted take profit {float(self.y_predict[0])}"
            )
            self.order("sell")
        else:
            logger.debug(
                f"Buy at {current_open_price} with predicted take profit {float(self.y_predict[0])}"
            )
            self.order("buy")

    def get_current_rate_to_predict(self):
        """
        Get the current rate, and open price
        """
        current_rate = mt5.copy_rates_from_pos(
            self.pair, config.TIMEFRAME_TO_TRADE, 0, 1
        )
        current_df = pd.DataFrame(current_rate)
        current_open_price = current_df.iloc[0]["open"]
        return current_open_price, current_df.drop(columns="close")

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
            logger.error(f"{self.pair} not found, cannot call order_check()")
            mt5.shutdown()
            quit()

        if not symbol_info.visible:
            logger.debug(f"{self.pair} is not visible, trying to switch on")
            if not mt5.symbol_select(self.pair, True):
                logger.error(f"symbol_select({self.pair}) failed, exit")
                mt5.shutdown()
                quit()
        logger.debug(
            f"{self.pair}'s Point: {mt5.symbol_info(self.pair).point}"
        )
        logger.debug(
            f"{self.pair}'s Ask Price: {mt5.symbol_info_tick(self.pair).ask}"
        )
        logger.debug(
            f"{self.pair}'s Ask Price with Point: {mt5.symbol_info_tick(self.pair).ask*mt5.symbol_info(self.pair).point}"
        )
        logger.debug(
            f"{self.pair}'s Bid Price: {mt5.symbol_info_tick(self.pair).bid}"
        )
        logger.debug(
            f"{self.pair}'s Bid Price with Point: {mt5.symbol_info_tick(self.pair).bid*mt5.symbol_info(self.pair).point}"
        )
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
            type_time=mt5.ORDER_TIME_DAY,
            type_filling=mt5.ORDER_FILLING_IOC,
        )
        logger.debug(
            f"Order Sent : by {self.pair} {self.lot} lots at {price} with deviation 20 points"
        )

    def raw_order(self, **kwargs):
        logger.debug(kwargs)
        result = mt5.order_send(kwargs)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order Send Failed, RETCODE = {result.retcode}")
        else:
            logger.debug(f"Order send done. Result: {result}")
        return result

    def check_existing_positions(self):
        """
        Returns if there's any existing positions.
        This is to help keep a limit to the number of orders a specific pair can handle.
        In this function, its to handle that there can only be 1 existing active order per symbol/pair.
        """
        logger.debug(f"Checking pair: {self.pair}")
        pos = mt5.positions_get(symbol=self.pair)
        logger.debug(f"{pos}")
        return len(pos) == 0


def main():
    if not mt5.initialize():
        logger.critical(f"MT5 Init failed, error code {mt5.last_error()}")
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
            if c.login() and c.check_existing_positions():
                c.analyze_and_trade()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logger.critical("Manually quit the program")
        raise
