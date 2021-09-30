import MetaTrader5 as mt5

ACCOUNT = 25115284
PASSWORD = "4zatlbqx"
SERVER = "MetaQuotes-Demo"
PAIRS = [
    # "EURAUD",
    # "EURUSD",
    # "GBPUSD",
    # "EURGBP",
    # "AUDUSD",
    # "USDJPY",
    # "EURCAD",
    "USDCAD"
]
TIMEZONE = "Asia/Brunei"
LOT_SIZE = 0.1
TIMEFRAME = mt5.TIMEFRAME_H1
TIMEFRAME_TO_TRADE = mt5.TIMEFRAME_M30
BARS_TO_TRAIN = 4500
COMMENT = "Python Bot v9"
DEBUG = False
