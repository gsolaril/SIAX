class PredictionEvaluation:
  """
  Encapsula todo el resultado de una evaluación de una predicción
  contra una serie de validación.

  Si se quieren agregar métricas, se pueden agregar en esta clase.
  """

  def __init__(self, mae = None, mse = None, plot = None):
    self.mae = mae
    self.mse = mse
    self.plot = plot

  def get_errors_description(self):
    """
    Devuelve una descripción (en string) de sobre los errores
    """

    return "Mean Absolute Error: " + str(self.mae) + '. '\
           "Mean Squared Error: " + str(self.mse) + '.'