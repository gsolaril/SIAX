import os
import numpy as np
import pandas as pd
import yfinance as yf
import keras as k
import datetime as dt
import matplotlib.pyplot as plt
import csv
import tensorflow as tf
from TimeSeriesUtils import TimeSeriesUtils

class ModelTesting:

  @staticmethod
  def plot_diff(time, series, forecast, scale_factor = 1, window_size = 50, from_t = 2400, to_t = 2600):

    """
      Imprime un gráfico a partir de la serie real y la predicha escalada
      en un factor de scale_factor. Hay veces que la serie se parece a la
      predicción pero le falta amplitud. El scale_factor la hace más amplia.
      Se pueden ir probando distintos factores al llamar a este método
    
      Keyword arguments:
        time -- el tiempo. Es el mismo para la serie y para el forecast
        series -- serie real
        forecast -- predicción
        scale_factor -- valor por el cual multiplicar a la predicción
        window_size -- tamaño de la ventana usado al predecir
        from_t -- como la serie es muy larga y el gráfico queda muy chico,
                  conviene imprimir sólo una porción. Este parámetro
                  es el t desde el cual imprimir
        to_t -- t hasta el cual imprimir
    """
    
    # Diferencio la serie
    diff_1 = series[window_size + 1:] - series[window_size:-1]
    
    # Me quedo con el tiempo para el cual hay predicciones
    time_1 = time[window_size + 1:]
    
    # Tomo la media de las predicciones
    forecast_mean = np.mean(forecast)
    
    # Ajusto el valor de la predicción moviendo la media hacia el cero,
    # luego escalando y finalmente devolviéndola a su lugar
    forecast_1 = (forecast - forecast_mean) * scale_factor + forecast_mean
    
    # Imprimo ambas series desde y hasta donde fue pedido
    from_t -= window_size
    to_t -= window_size
    plot_series((time_1, diff_1), (time_1, forecast_1), from_t, to_t)

  @staticmethod
  def test_model(model_constructor, get_dataset, window_size = 50, epochs = 50):
    """
      Esta función recibe un constructor de una clase que herede de WindowBasedModel,
      así como también un método para obtener el dataset.
      La función primero llama al método get_dataset(), lo divide entre
      datos de training y de testing, y luego se lo pasa al modelo que se construye
      con el constructor que se pasa por parámetro.
      Finalmente predice con toda la serie.
    
      Devuelve:
        model_constructor -- el constructor del modelo a usar
        time -- el tiempo
        series -- la serie real
        forecast -- la serie que predijo el modelo
    """
    
    # Obtengo la serie
    time, series, split_size = get_dataset()
    
    time_train, x_train, time_valid, x_valid = TimeSeriesUtils.split_dataset(time, series, split_size)
    
    # Creo el modelo
    model = model_constructor(epochs = epochs, window_size = window_size)
    
    # Imprimo qué modelo es
    print(model.describe())
    
    # Entreno
    model.train(x_train)
    
    # Predigo
    forecast = model.predict(series)
    
    # Guardo el modelo en un h5 en la carpeta tmp
    model.save_model()
    
    return model, time, series, forecast