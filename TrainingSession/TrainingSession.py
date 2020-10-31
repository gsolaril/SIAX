import os
import time
import numpy as np
from os import path
from SIAX.Backtest.Backtesting_Vectorizado import Backtest
from SIAX.TrainingSession.PredictionEvaluator import PredictionEvaluator

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

  * save_full_predictions: (opcional) si se setea en True, el array completo de predicción y validación
  se van a guardar en un csv. Esto ocupa mucho espacio y generalmente no aporta mucha información, por
  lo que su valor por defecto es False.
  """

  def __init__(self, model, training_market_data, results_storage = 'results', save_full_predictions = False):

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

    # Guardar toda la predicción ocupa demasiado espacio, pero si por algún motivo
    # queremos guardarlas, seteando este parámetro en True, se guradan en un csv
    self._save_predictions = save_full_predictions

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
    """
    Se llama al método train del modelo pasándole la serie de datos de
    training que se obtuvo a partir de la inforamción con la que se configuró
    la Training Session.

    Luego se predice con los datos de validación y se calcula una evaluación
    de la predicción del tipo PredictionEvaluation.
    """

    # Creo un identificador nuevo porque vuelvo a correr
    self.__reset_identifier__()

    # Entreno el modelo con el set correspondiente
    self._model.train(self._train)

    # Luego predigo en base al validation set
    self._forecast = self._model.predict(self._valid)

    # Creo un evaluador para la serie de validación y la predicción
    evaluator = PredictionEvaluator(self._valid, self._forecast)

    # Guardo la evaluación de la predicción.
    self._evaluation = evaluator.evaluate()

    # Persisto los resultados
    self.__persist__()


  def set_backtesting_info(self, backtesting_market_data, backtesting_strategy, verbose = 1):
    """
    Setea los datos con los cuales va a hacer el backtesting.
    Para correr el backtesting, se debe llamar al método run_backtest.

    Argumentos:
    backtesting_market_data: una instancia de MarketData con los datos a utilizar en el backtesting
    backtesting_strategy: la estrategia de trading a backtestear
    verbose: el nivel de verbose que se quiere usar en el bactesting:
            0: no se imprime nada
            1: se imprime sólo una línea que se va pisando
            2: se imprime una línea abajo de la otra
    """

    # Si ya había datos de backtesting, quiere decir que los estamos modificando,
    # por lo tanto reseteamos el identificador porque es otra sesión.
    if self._backtesting_market_data and self._backtesting_strategy:
      self.__reset_identifier__()

    # Guardo los datos que recibo por parámetro
    self._backtesting_market_data = backtesting_market_data
    self._backtesting_strategy = backtesting_strategy

    # Creo el backtest con la data de test y el nivel de verbose correspondiente
    self._backtest = Backtest(backtesting_market_data.dataset, verbose = verbose)


  def run_backtest(self):
    """
    Corre el backtest y guarda los resultados.
    """
    assert self._backtest, "No hay un backtest configurado"

    self._backtest.run(self._backtesting_strategy)
    self.__persist__()


  def __reset_identifier__(self):
    """
    Cada vez que se cambia algún parámetro, se crea un nuevo identificador.
    De esta manera, ante el menor cambio generamos resultados en un directorio distinto
    y no perdemos el output de ningún training o testing.
    """
    self._identifier = str(int(time.time() * 10000))


  def __persist__(self):
    """
    Dejo un registro en archivos de todo lo que sucedió hasta el momento en la sesión.
    Sé que al menos el training del modelo se hizo, pero el backtesting puede haberse hecho
    como no. Si el modelo no se modificó y se corre el backtesting, reutilizo el directorio
    donde ya guardé los datos de training.

    Si hubo cualquier tipo de cambio, entonces el identificador se modificó y se genera un nuevo directorio.
    """

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

    # Si corresponde, guardo el resultado completo de la predicción
    self.__persisst_arrays__(this_result_folder)

    # Guardo el resultado de evaluar la predicción contra el validation set
    with open(path.join(this_result_folder, "prediction_evaluation.txt"), "w") as text_file:
        text_file.write(self._evaluation.get_errors_description())

    # Además, guardo el gráfico que las compara
    plot_path = path.join(this_result_folder, "prediction_vs_validation.png")

    # Pero sólo si no existe. Porque si existe es porque es igual.
    if not os.path.exists(plot_path):
      self._evaluation.plot.savefig(plot_path)

    # Si se corrió el backtesting, guardo el csv con los resultados
    if self._backtest and not self._backtest.stats().empty:
      self._backtest.stats().to_csv(path.join(this_result_folder, "backtesting_statistics.csv"))


  def __persisst_arrays__(self, directory):
    """
    Si self._save_predictions es True, guardo los arrays de validación y predicción completos
    """
    if self._save_predictions:
      np.savetxt(path.join(directory, "validation_array.csv"), self._valid, delimiter=",")
      np.savetxt(path.join(directory, "prediction_array.csv"), self._forecast, delimiter=",")