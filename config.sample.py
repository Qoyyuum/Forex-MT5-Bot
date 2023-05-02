import MetaTrader5 as mt5

ACCOUNT = 53774688
PASSWORD = "3jgvhvxe"
SERVER = "MetaQuotes-Demo"
PAIRS = [
    "EURAUD",
    "EURUSD",
    "GBPUSD",
    "EURGBP",
    "AUDUSD",
    "USDJPY",
    "EURCAD",
    "USDCAD",
]
TIMEZONE = "Asia/Brunei"
LOT_SIZE = 0.1
TIMEFRAME = mt5.TIMEFRAME_M1
TIMEFRAME_TO_TRADE = mt5.TIMEFRAME_M30
BARS_TO_TRAIN = 4500
COMMENT = "Trading Bot v1"
DEBUG = False
NO_CONCURRENT_TRADES = 0  # 0 to always maintain 1 concurrent trade
