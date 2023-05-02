import logging
import logging.config
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

import config

logging.config.fileConfig("logging.conf")

logger = logging.getLogger("app" if config.DEBUG else "root")


@dataclass
class Client:
    __slots__ = [
        "account",
        "password",
        "server",
        "pair",
        "lot",
        "timeframe",
        "y_predict",
        "stop_loss",
    ]
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

    def determine_signal(
        self, open_price: float, predicted_price: float
    ) -> Any:
        """Determine the trading signal based on which price is higher or lower"""
        if open_price > predicted_price:
            logger.debug(
                f"Sell at {open_price} with predicted take profit {predicted_price}"
            )
            self.stop_loss = self.get_stop_loss(
                mt5.symbol_info_tick(self.pair).bid, predicted_price
            )
            return self.order("sell")
        elif open_price < predicted_price:
            logger.debug(
                f"Buy at {open_price} with predicted take profit {predicted_price}"
            )
            self.stop_loss = self.get_stop_loss(
                mt5.symbol_info_tick(self.pair).ask, predicted_price
            )
            return self.order("buy")
        else:
            logger.warn(
                "Miraculously the open price and the predicted price are exactly the same. Not sure what to do"
            )
        return False

    def build_dataset(
        self, df_data: np.ndarray, lookup_data: int = 1
    ) -> tuple[Any, Any]:
        """Split a dataframe and split the dataset to train a model"""
        from sklearn.model_selection import train_test_split

        df_data["adjclose"] = df_data["close"].shift(
            periods=-lookup_data, fill_value=0
        )
        df_x = df_data.drop(columns="adjclose")

        x_train, _xtest, y_train, _ytest = train_test_split(
            df_x,
            df_data["adjclose"],
            test_size=0.2,
            random_state=42,
            shuffle=True,
        )

        return x_train, y_train

    def analyze_and_trade(
        self, rates: np.ndarray = None, current_rates: np.ndarray = None
    ) -> None:
        """Analyze the past X rates and trade on the current open price. X rates is configured by BARS_TO_TRAIN."""
        while rates is None:
            rates = mt5.copy_rates_from_pos(
                self.pair, self.timeframe, 1, config.BARS_TO_TRAIN
            )

        while current_rates is None:
            current_rates = mt5.copy_rates_from_pos(
                self.pair, self.timeframe, 0, 1
            )

        x_train, y_train = self.build_dataset(pd.DataFrame(rates))
        model = self.get_model_to_predict(x_train, y_train)
        current_open_price, to_predict = self.get_current_rate_to_predict(
            current_rates
        )
        self.y_predict = model.predict(to_predict)
        return self.determine_signal(
            current_open_price, float(self.y_predict[0])
        )

    def get_stop_loss(
        self, open_price: float, predicted_price: float
    ) -> float:
        if open_price > predicted_price:
            return open_price + ((open_price - predicted_price))
        else:
            return open_price - ((predicted_price - open_price))

    def get_current_rate_to_predict(self, current_rate: np.ndarray = None):
        """
        Get the current rate, and open price
        """
        current_df = pd.DataFrame(current_rate)
        current_open_price = current_df.iloc[0]["open"]
        return current_open_price, current_df

    def get_model_to_predict(self, x_train, y_train):
        """
        Build a model to fit with the x and y training data set and fit.

        Returns the built and learned model

        TODO: Investigate and find out what's a better model if not better from scikit-learn's Linear Regression.
        """
        from sklearn.linear_model import LinearRegression

        return LinearRegression().fit(x_train, y_train)

    def set_lot_size(self) -> float:
        """Get from History Orders. If the last History Order was a loss, double the lot size in the next trade."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=4)
        logger.debug(f"!!!CHECKING HISTORY DEALS FOR {self.pair}!!!")
        history_deals = mt5.history_deals_get(
            from_date, to_date, group=self.pair
        )
        if history_deals is None:
            logger.debug(
                f"No history orders with this pair: {self.pair}. Error code = {mt5.last_error()}"
            )
            return self.lot
        elif len(history_deals) > 0:
            comment = history_deals[len(history_deals) - 1].comment
            if "tp" in comment or "sl" not in comment:
                return self.lot
            traded_volume = history_deals[len(history_deals) - 1].volume
            return traded_volume + traded_volume
        else:
            logger.debug(f"Something went wrong. Error: {mt5.last_error()}")
        return self.lot

    def order(self, signal: str) -> bool:
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
        order_type, price = (
            (mt5.ORDER_TYPE_SELL, symbol_info_tick.bid)
            if signal == "sell"
            else (mt5.ORDER_TYPE_BUY, symbol_info_tick.ask)
        )
        self.lot = self.set_lot_size()
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
        return True

    def raw_order(self, **kwargs):
        """Sends the order from kwargs returns the result dictionary"""
        logger.debug(kwargs)
        result = (
            mt5.order_check(kwargs) if config.DEBUG else mt5.order_send(kwargs)
        )
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(
                f"Order Send Failed for {self.pair}, RETCODE = {result.retcode}"
            )
        else:
            logger.info(f"Order send done. Result: {result}")
        logger.debug(f"Result Type: {type(result)}")
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
        return pos is None or len(pos) == config.NO_CONCURRENT_TRADES


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
                c.analyze_and_trade()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logger.critical("Manually quit the program")
