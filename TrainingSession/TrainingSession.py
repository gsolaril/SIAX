import os
import time
import numpy as np
import datetime
from datetime import timedelta
from os import path
from SIAX.Backtest.Backtesting_Vectorizado import Backtest
from SIAX.NeuralNetworks.WindowGenerator import WindowGenerator
from SIAX.TrainingSession.PredictionEvaluator import PredictionEvaluator
from SIAX.PreProcessing.DataFrameProcessing import DataFrameProcessing
from SIAX.PreProcessing.PreProcessor import PreProcessor

class TrainingSession:
  """
  Esta clase maneja toda la sesión de training y backtesting
  y deja registros de cada corrida en un directorio.

  La clase requiere:

  * model: Un modelo que tenga los siguientes 3 métodos:

  *** train: que reciba una serie de tiempo
  *** call: que reciba un dataframe y que prediga el siguiente valor de una de sus features
  *** save_model: que reciba un directorio y guarde su representación en archivos ahí adentro

  *** Además tiene que tener una propiedad `window_size` que represente el tamaño de la ventana que usa
  
  * training_market_data: Un objeto de la clase MarketData con el cual va a entrenar

  * validation_market_data: Un objeto de la clase MarketData con el cual va a hacer la validación

  * pre_processor: (opcional) un callable que reciba un dataframe, lo modifique y lo devuelva.
    Por defecto usa el preprocesador PreProcessor que no hace ningún cambio.
  
  * results_storage: (opcional) el nombre del directorio donde guardar los resultados.
    Por defecto los va a guardar en './results'

  * save_full_predictions: (opcional) si se setea en True, el array completo de predicción y validación
  se van a guardar en un csv. Esto ocupa mucho espacio y generalmente no aporta mucha información, por
  lo que su valor por defecto es False.
  """

  def __init__(self, model, training_market_data, validation_market_data, pre_processor = PreProcessor(), results_storage = 'results', save_full_predictions = False):

    # Un identificador único que se va reseteando si cambia algo en la sesión
    self.__reset_identifier__()

    # Modelo con el que se va a predecir
    self._model = model

    # Dónde guardar los resultados
    self.results_storage = results_storage

    # Market data usada para el training del modelo
    self._training_market_data = training_market_data

    # Market data usada para validación
    self._validation_market_data = validation_market_data

    # El procesador de dataframes a usar
    self._window_size = model.window_size

    # La serie que va a predecir
    self._forecast = None

    # Guardar toda la predicción ocupa demasiado espacio, pero si por algún motivo
    # queremos guardarlas, seteando este parámetro en True, se guradan en un csv
    self._save_predictions = save_full_predictions

    # Un preprocesador que recibe un dataframe, lo procesa y lo devuelve
    self.pre_processor = pre_processor

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

    ## Training Data

    # Pre procesamiento de los datos    
    training_data = self.pre_processor(self._training_market_data.dataset)

    # Agrupo los datos en ventanas. Shuffle = True porque durante el training es preferible que la data no esté ordenada
    trining_windows = WindowGenerator(training_data, self._window_size).make_dataset(training_data, shuffle=True)


    ## Validation Data

    # Pre procesamiento de los datos
    validation_data = self.pre_processor(self._validation_market_data.dataset)

    # Agrupo los datos en ventanas. Shuffle = False porque quiero la información en orden para comparar y graficar
    val_windows = WindowGenerator(validation_data, self._window_size).make_dataset(validation_data, shuffle=False)

    # Entreno el modelo con el set correspondiente y pasándole la data de validación para imprimir métricas
    self._model.train(trining_windows, validation_data = val_windows)

    # Predigo usando las ventanas de validación
    self._forecast = np.array([yhat for x, y in val_windows for yhat in self._model.call(x)])

    # Quito las dimensiones extra
    self._forecast = np.squeeze(self._forecast)

    # Formateo los true labels de las ventanas de validación
    self._valid = np.array([y for _, y_batch in val_windows for y in y_batch])

    # Quito las dimensiones extra
    self._valid = np.squeeze(self._valid)

    assert len(self._forecast) == len(self._valid), f'Error. Forecast length: {len(self._forecast)}, Validation length: {len(self._valid)}'

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
    self._identifier = f"{(datetime.datetime.now(datetime.timezone.utc) + timedelta(hours=-3)):%Y%m%d%H%M%S%f}"


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

    with open(path.join(this_result_folder, "stats.csv"), "w") as text_file:
        text_file.write(self._get_stats())

  def _get_stats(self):
    dt = f"{(datetime.datetime.now(datetime.timezone.utc) + timedelta(hours=-3)):%Y-%m-%d %H:%M:%S}"
    mae = self._evaluation.mae
    mse = self._evaluation.mse
    correct_direction = self._evaluation.correct_direction
    validation_size = self._valid.shape[0]
    identifier = self._identifier
    training_data = self._training_market_data.summary()

    return f"Identifier,DateTime,TrainingData,MAE,MSE,Validation Size,Correct Direction\n" + \
      f"{identifier},{dt},{training_data},{mae},{mse},{validation_size},{correct_direction}"

  def __persisst_arrays__(self, directory):
    """
    Si self._save_predictions es True, guardo los arrays de validación y predicción completos
    """
    if self._save_predictions:
      np.savetxt(path.join(directory, "validation_array.csv"), self._valid, delimiter=",")
      np.savetxt(path.join(directory, "prediction_array.csv"), self._forecast, delimiter=",")