from TimeSeriesUtils import TimeSeriesUtils

class MarketData:

  def __init__(self, symbol, frequency, start_date, rows, dataset):
    self.symbol = symbol
    self.frequency = frequency
    self.start_date = start_date
    self.rows = rows
    self.dataset = dataset

  def describe(self):
    return self.symbol + " con frecuencia " + self.frequency +\
          ". Desde " + self.start_date + ". " + str(self.rows) + " filas."
  
  def to_series_dataset(self):

    time, series = TimeSeriesUtils.get_time_series_from_dataframe(self.dataset)

    _, series_train, _, series_valid = TimeSeriesUtils.split_dataset(time, series)

    return series_train, series_valid