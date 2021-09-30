import logging
import logging.config
from dataclasses import dataclass

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

import config

logging.config.fileConfig("logging.conf")

logger = logging.getLogger("app" if config.DEBUG else "root")


@dataclass
class Client:
    account: int
    password: str
    server: str
    pair: str
    lot: float
    timeframe: np.ndarray

    def login(self) -> bool:
        "Client login"
        if mt5.login(
            login=self.account, password=self.password, server=self.server
        ):
            logger.debug(
                f"Logged in to {self.server} with account {self.account}"
            )
            return True
        else:
            logger.critical(
                f"Failed to login to {self.server} with account {self.account}"
            )
            return False

    def analyze_and_trade(self, rates: np.ndarray) -> None:
        """Analyze the past 100 rates and trade on the current open price"""
        while rates is None:
            rates = mt5.copy_rates_from_pos(
                self.pair, self.timeframe, 1, config.BARS_TO_TRAIN
            )
            logger.debug(f"Fetched rates for {self.pair} :\n{rates}")

        df_data = pd.DataFrame(rates)
        df_x = df_data.drop(columns="close")
        df_y = df_data["close"]

        x_train, x_test, y_train, y_test = train_test_split(
            df_x, df_y, test_size=0.2, random_state=0
        )
        # logger.debug(f"x_train :\n{x_train}")
        # logger.debug(f"x_test :\n{x_test}")
        # logger.debug(f"y_train :\n{y_train}")
        # logger.debug(f"y_test :\n{y_test}")
        model = self.get_model_to_predict(x_train, y_train)
        logger.debug(f"Trained Model:\n{model}")
        current_open_price, to_predict = self.get_current_rate_to_predict()
        self.y_predict = model.predict(to_predict)
        if current_open_price > float(self.y_predict[0]):
            logger.debug(
                f"Sell at {current_open_price} with predicted take profit {float(self.y_predict[0])}"
            )
            self.stop_loss = self.get_stop_loss(
                mt5.symbol_info_tick(self.pair).bid, float(self.y_predict[0])
            )
            self.order("sell")
        elif current_open_price < float(self.y_predict[0]):
            logger.debug(
                f"Buy at {current_open_price} with predicted take profit {float(self.y_predict[0])}"
            )
            self.stop_loss = self.get_stop_loss(
                mt5.symbol_info_tick(self.pair).ask, float(self.y_predict[0])
            )
            self.order("buy")
        else:
            logger.warn(
                "Miraculously the open price and the predicted price are exactly the same. Not sure what to do"
            )

    def get_stop_loss(
        self, open_price: float, predicted_price: float
    ) -> float:
        if open_price > predicted_price:
            return open_price + ((open_price - predicted_price) * 2)
        else:
            return open_price - ((predicted_price - open_price) * 2)

    def get_current_rate_to_predict(self):
        """
        Get the current rate, and open price
        """
        current_rate = mt5.copy_rates_from_pos(
            self.pair, config.TIMEFRAME, 0, 1
        )
        current_df = pd.DataFrame(current_rate)
        current_open_price = current_df.iloc[0]["open"]
        return current_open_price, current_df.drop(columns="close")

    def get_model_to_predict(self, x_train, y_train):
        """
        Build a model to fit with the x and y training data set and fit.

        Returns the built and learned model

        TODO: Investigate and find out what's a better model if not better from scikit-learn's Linear Regression.
        """
        from sklearn.linear_model import LinearRegression

        return LinearRegression().fit(x_train, y_train)

    def order(self, signal: str) -> None:
        """Depending on the param signal, this will place an order for BUY or SELL"""
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
        symbol_info_tick = mt5.symbol_info_tick(self.pair)
        # logger.debug(
        #     f"{self.pair}'s Point: {symbol_info.point}"
        # )
        # logger.debug(
        #     f"{self.pair}'s Ask Price: {symbol_info_tick.ask}"
        # )
        # logger.debug(
        #     f"{self.pair}'s Ask Price with Point: {symbol_info_tick.ask*symbol_info.point}"
        # )
        # logger.debug(
        #     f"{self.pair}'s Bid Price: {symbol_info_tick.bid}"
        # )
        # logger.debug(
        #     f"{self.pair}'s Bid Price with Point: {symbol_info_tick.bid*symbol_info.point}"
        # )
        order_type, price = (
            (mt5.ORDER_TYPE_SELL, symbol_info_tick.bid)
            if signal == "sell"
            else (mt5.ORDER_TYPE_BUY, symbol_info_tick.ask)
        )
        self.raw_order(
            action=mt5.TRADE_ACTION_DEAL,
            symbol=self.pair,
            volume=self.lot,
            type=order_type,
            price=price,
            tp=float(self.y_predict[0]),
            sl=float(self.stop_loss),
            deviation=20,
            magic=20210927,
            comment=config.COMMENT,
            type_time=mt5.ORDER_TIME_DAY,
            type_filling=mt5.ORDER_FILLING_IOC,
        )
        logger.debug(
            f"Order Sent : by {self.pair} {self.lot} lots at {price} with deviation 20 points"
        )

    def raw_order(self, **kwargs):
        """Sends the order from kwargs returns the result dictionary"""
        logger.debug(kwargs)
        result = (
            mt5.order_check(kwargs) if config.DEBUG else mt5.order_send(kwargs)
        )
        while result.retcode == mt5.TRADE_RETCODE_INVALID_STOPS:
            self.analyze_and_trade()
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(
                f"Order Send Failed for {self.pair}, RETCODE = {result.retcode}"
            )
        else:
            logger.info(f"Order send done. Result: {result}")
        return result

    def check_existing_positions(self) -> bool:
        """
        Returns if there's any existing positions.
        This is to help keep a limit to the number of orders a specific pair can handle.
        In this function, its to handle that there can only be 1 existing active order per symbol/pair.
        """
        logger.debug(f"Checking pair: {self.pair}")
        pos = mt5.positions_get(symbol=self.pair)
        logger.debug(f"{pos}")
        return pos is None or len(pos) == 0


def main() -> None:
    """Start the bot"""
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
                c.analyze_and_trade(rates=None)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logger.critical("Manually quit the program")
