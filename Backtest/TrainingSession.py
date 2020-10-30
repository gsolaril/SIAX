import os
import time
import numpy as np
from os import path
from Backtesting_Vectorizado import Backtest

class TrainingSession:
  """
  Esta clase maneja toda la sesión de training y backtesting
  y deja registros de cada corrida en un directorio.

  La clase requiere:

  * model: Un modelo que tenga los siguientes 3 métodos:

  *** train: que reciba una serie de tiempo
  *** predict: que reciba una serie de tiempo y que prediga el siguiente valor
  *** save_model: que reciba un directorio y guarde su representación en archivos ahí adentro.

  Además, no tiene que fallar si se le consulta la propiedad transform_series.
  Puede ser None pero tiene que tenerla definida.

  * training_market_data: Un objeto de la clase MarketData con el cual va a entrenar

  * results_storage: (opcional) el nombre del directorio donde guardar los resultados.
    Por defecto los va a guardar en './results'

  """

  def __init__(self, model, training_market_data, results_storage = 'results'):

    # Un identificador único que se va reseteando si cambia algo en la sesión
    self.__reset_identifier__()

    # Modelo con el que se va a predecir
    self._model = model

    # Dónde guardar los resultados
    self.results_storage = results_storage

    # Market data usada para el training del modelo
    self._training_market_data = training_market_data
    self._train, self._valid = self._training_market_data.to_series_dataset()

    # La serie que va a predecir
    self._forecast = None

    # Opcionalmente se puede transformar el validation set
    # En general vamos a estimar la diferencia en los valores de la serie
    # y no los valores en sí. Acá transformamos la serie de ese modo.
    if self._model.transform_series:
      self._valid = self._model.transform_series(self._valid)

    # Para Backtesting
    self._backtesting_market_data = None
    self._backtesting_strategy = None
    self._backtest = None


  def run_training(self):
    self.__reset_identifier__()
    self._model.train(self._train)
    self._forecast = self._model.predict(self._valid)
    self.__persist__()


  def set_backtesting_info(self, backtesting_market_data, backtesting_strategy, verbose = 1):
    if self._backtesting_market_data and self._backtesting_strategy:
      self.__reset_identifier__()

    self._backtesting_market_data = backtesting_market_data
    self._backtesting_strategy = backtesting_strategy
    self._backtest = Backtest(backtesting_market_data.dataset, verbose = verbose)


  def run_backtest(self):
    assert self._backtest, "No hay un backtest configurado"

    self._backtest.run(self._backtesting_strategy)
    self.__persist__()


  def __reset_identifier__(self):
    self._identifier = str(int(time.time() * 10000))


  def __persist__(self):

    # Me aseguro de que exista la carpeta que guarda todos los resultados
    if not os.path.exists(self.results_storage):
      os.makedirs(self.results_storage)

    # Me fijo si ya creé una carpeta para estos resultados
    this_result_folder = path.join(self.results_storage, self._identifier)

    if not os.path.exists(this_result_folder):
      os.makedirs(this_result_folder)

    # En esa carpeta guardo la market data que usé para el training
    with open(path.join(this_result_folder, "training_market_data.txt"), "w") as text_file:
      text_file.write(self._training_market_data.describe())

    if self._backtesting_market_data:
      # En esa carpeta guardo la market data que usé para el backtesting
      with open(path.join(this_result_folder, "backtesting_market_data.txt"), "w") as text_file:
        text_file.write(self._backtesting_market_data.describe())

    # Guardo también el modelo que usé
    self._model.save_model(this_result_folder)

    # Guardo también la predicción junto con los valores reales
    np.savetxt(path.join(this_result_folder, "validation_set.txt"), self._valid, delimiter=",")
    np.savetxt(path.join(this_result_folder, "prediction.txt"), self._forecast, delimiter=",")

    if self._backtest:
      if not self._backtest.stats().empty:
        self._backtest.stats().to_csv(path.join(this_result_folder, "backtesting_statistics.csv"))