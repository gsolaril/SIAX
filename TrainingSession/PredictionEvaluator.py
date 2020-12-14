import numpy as np
import matplotlib.pyplot as plt
from SIAX.TrainingSession.PredictionEvaluation import PredictionEvaluation

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
    mae = self._calculate_mae()

    # Calculo el Mean Squared Error
    mse = self._calculate_mse()

    correct_direction = self._calculate_correct_direction()

    # Obtengo el gráfico que compara ambas series
    plot = self._get_plot()

    # Devuelvo un PredictionEvaluation con todos los cálculos
    return PredictionEvaluation(mae, mse, correct_direction, plot)


  def _get_plot(self):
    """
    Devuelve un gráfico comparando la predicción y la serie de validación
    """

    time = range(self._prediction_size)

    # Inicializo del gráfico
    plt.figure(figsize=(30, 6))
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.grid(True)
    
    plt.plot(time, self._validation)
    plt.plot(time, self._prediction)

    return plt


  def _calculate_mae(self):
    """
    Calcula el Mean Absolute Error
    """
    return np.sum(np.abs(self._validation - self._prediction)) / self._prediction_size


  def _calculate_mse(self):
    """
    Calcula el Mean Squared Error
    """
    return np.sum((self._validation - self._prediction) ** 2) / self._prediction_size

  def _calculate_correct_direction(self):
    """
    Devuelve el porcentaje de veces que acertó la dirección
    en que la serie se mueve. Es decir si predijo que subía y subió
    o si predijo que bajaba y bajó.

    Si predijo 0 o el real fue 0, no lo toma como válido.
    """
    return np.sum((self._prediction  * self._validation) > 0) * 100 / self._prediction_size