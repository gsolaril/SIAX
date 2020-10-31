import numpy as np
from TimeSeriesUtils import TimeSeriesUtils
from PredictionEvaluation import PredictionEvaluation

class PredictionEvaluator:
  """
  A partir de la serie de validación y de la predicción que devolvió el modelo
  genera una PredictionEvaluation con los resultados de evaluarlos.
  """

  def __init__(self, validation, prediction):

    # Guardo la cantidad de elementos que tiene de la predicción
    self._prediction_size = prediction.shape[0]

    # Guardo la predicción
    self._prediction = prediction

    # De la serie de validación descarto los elementos para los cuales
    # no generé ninguna predicción
    self._validation = validation[-self._prediction_size:]


  def evaluate(self):
    """
    Hace la evaluación a partir de las series con las que se creó.
    Esto es un método separado porque en un futuro puede tardar más tiempo.
    
    Devuelve:
    Una PredictionEvaluation con la información de la evaluación
    """

    # Calculo el Mean Absolute Error
    mae = self._calculate_mae(self._validation, self._prediction)

    # Calculo el Mean Squared Error
    mse = self._calculate_mse(self._validation, self._prediction)

    # Obtengo el gráfico que compara ambas series
    plot = self._get_plot()

    # Devuelvo un PredictionEvaluation con todos los cálculos
    return PredictionEvaluation(mae, mse, plot)


  def _get_plot(self):
    """
    Devuelve un gráfico comparando la predicción y la serie de validación
    """

    t_s_prediction = (range(self._prediction_size), self._prediction)
    t_s_validation = (range(self._prediction_size), self._validation)

    return TimeSeriesUtils.get_plot_series([t_s_prediction, t_s_validation])


  def _calculate_mae(self, validation, prediction):
    """
    Calcula el Mean Absolute Error
    """
    return np.sum(np.abs(validation-prediction)) / prediction.shape[0]


  def _calculate_mse(self, validation, prediction):
    """
    Calcula el Mean Squared Error
    """
    return np.sum((validation-prediction) ** 2) / prediction.shape[0]