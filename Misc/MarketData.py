from SIAX.NeuralNetworks.WindowGeneratorFactory import WindowGeneratorFactory

class MarketData:

  def __init__(self, symbol, frequency, start_date, rows, dataset, col_to_predict = "Close"):
    self.symbol = symbol
    self.frequency = frequency
    self.start_date = start_date
    self.rows = rows
    self.dataset = dataset
    self.col_to_predict = col_to_predict

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
  
  def to_window_generator(self, window_size):
    """
    Devuelve dos series de tiempo. Una de training y una de validación.
    El 80% de la serie va a ser de training y el 20 de validación.
    """

    return WindowGeneratorFactory.build_multi_input_diff(self.dataset, [self.col_to_predict], window_size)

  def get_features(self):
    return self.dataset.drop([self.col_to_predict])

  def get_labels(self):
    return self.dataset[self.col_to_predict]