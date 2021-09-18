from datetime import datetime
import pandas as pd
import MetaTrader5 as mt5
import csv, config
from tqdm import tqdm
 
 

def get_pair(pair):
    """
    request ticks from :pair from early 2020
    """
    for p in pair:
        print(f"Getting {p} data")
        ticks = mt5.copy_ticks_from(p, datetime(2020,1,27,13), 1000000, mt5.COPY_TICKS_ALL)
        print(f"Tick Data received: {len(ticks)}")
        write_to_csv(ticks, p)
    # create DataFrame out of the obtained data
    # ticks_frame = pd.DataFrame(audusd_ticks)
    # convert time in seconds into the datetime format
    # ticks_frame['time']=pd.to_datetime(ticks_frame['time'], unit='s')

def write_to_csv(data, pair):
    """
    Write data pair into a CSV file
    """
    # import csv
    # from datetime import datetime
    # EURUSD = (1580189529, 1.63118, 1.63152, 0., 0, 1580189529748, 130, 0.)

    now = datetime.now().strftime("%Y%m%d%H%M%S")
    with open(f"{pair}{now}.csv", "w") as f:
        writer = csv.writer(f)
        print(f"Writing CSV for {pair}")
        for d in tqdm(data):
            writer.writerow(d)

    print(f"Write Complete for {pair}")

if __name__ == '__main__':
    # connect to MetaTrader 5
    if not mt5.initialize():
        print("initialize() failed")
        mt5.shutdown()
    
    # # request connection status and parameters
    # print(mt5.terminal_info())
    # # get data on MetaTrader 5 version
    # print(mt5.version())
    print("Program Start")
    get_pair(config.PAIRS)