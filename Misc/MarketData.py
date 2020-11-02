from SIAX.Misc.TimeSeriesUtils import TimeSeriesUtils

class MarketData:

  def __init__(self, symbol, frequency, start_date, rows, dataset):
    self.symbol = symbol
    self.frequency = frequency
    self.start_date = start_date
    self.rows = rows
    self.dataset = dataset

  def describe(self):
    """
    Devuelve un string con la descripción de la metadata
    """
    return self.symbol + " con frecuencia " + self.frequency +\
          ". Desde " + self.start_date + ". " + str(self.rows) + " filas."

  def summary(self):
    """
    Devuelve la información sumarizada para ser insertada en una tabla
    """

    return f"{self.symbol}|{self.frequency}|{self.start_date}|{self.rows}"
  
  def to_series_dataset(self):
    """
    Devuelve dos series de tiempo. Una de training y una de validación.
    El 80% de la serie va a ser de training y el 20 de validación.
    """

    time, series = TimeSeriesUtils.get_time_series_from_dataframe(self.dataset)

    _, series_train, _, series_valid = TimeSeriesUtils.split_dataset(time, series)

    return series_train, series_valid