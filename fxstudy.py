from lazypredict.Supervised import LazyRegressor
from sklearn.model_selection import train_test_split
import pandas as pd

data = pd.read_csv('GBPUSD20210414164534.csv')
print(data.head())
# Returns named time, open, high, low, close, tick_volume and real_volume
# train_size = int(0.7 * len(data))

# train_set = data[:train_size]
# test_set = data[train_size:]

# print("Train Set : ", len(train_set))
# print("Test Set : ", len(test_set))

# reg = LazyRegressor(verbose=1, ignore_warnings=False, custom_metric=None)
# models, predictions = reg.fit(train_set, test_set)

# print(models)