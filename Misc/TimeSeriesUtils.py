import os
import numpy as np
import pandas as pd
import yfinance as yf
import keras as k
import datetime as dt
import matplotlib.pyplot as plt
import csv

class TimeSeriesUtils:

    def get_time_series_from_file(filename = 'MELI(5m).csv', data_idx = 2, time_step_idx = None):
      """
        Lee una serie de tiempo desde un archivo csv
        
        Keyword arguments:
        filename -- nombre del archivo csv
        data_idx -- columna en la cual está la serie de tiempo
        time_step_idx -- columna en la cual está el tiempo
      """

      time_step = []
      sunspots = []

      idx = 0

      with open(filename) as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader)
        for row in reader:
          sunspots.append(float(row[data_idx]))

          if time_step_idx != None:
            time_step.append(int(row[time_step_idx]))
          else:
            time_step.append(idx)
            idx += 1

      series = np.array(sunspots)
      time = np.array(time_step)
      plt.figure(figsize=(10, 6))
      plot_series((time, series))

      return time, series


    def plot_series(time_series_1, time_series_2 = None, start=0, end=None, figsize=(30, 6), format="-"):
      """
        Imprime un gráfico de una serie de tiempo.
        Recibe el tiempo y la serie además de dónde empieza y dónde termina la serie
        Por defecto el gráfico incluye a toda la serie
        
        Keyword arguments:
        time_series_1 -- serie de tiempo 1 de la forma (tiempo, serie)
        time_series_2 -- serie de tiempo 2 de la forma (tiempo, serie)
      """

      # Inicializo del gráfico
      plt.figure(figsize=figsize)
      plt.xlabel("Time")
      plt.ylabel("Value")
      plt.grid(True)

      # Desarmo la tupla 1
      time_1, series_1 = time_series_1

      # Agrego la serie 1 al gráfico
      plt.plot(time_1[start:end], series_1[start:end], format)

      # Si hay una serie 2, la incluyo de la misma manera
      if time_series_2 != None:
        time_2, series_2 = time_series_2
        plt.plot(time_2[start:end], series_2[start:end], format)
      
      plt.show()
    

    def get_days_to_request(interval):
      """
        Yahoo sólo permite descargar información de los últimos días
        y la cantidad de días hacia atrás que permite depende de la frecuencia
        
        Keyword arguments:
        interval -- intervalo entre datapoints
      """

      return {
            '1d': 365,
            '5m': 59,
            '1m': 7
        }[interval]


    def get_from_yahoo(instrument = "AMZN", interval = "5m"):
      """
        Pide a Yahoo los datos del instrumento pasado por parámetro con la frecuencia indicada

        Keyword arguments:
        instrument -- instrumento para el cual se quiere predecir
        interval -- intervalo entre datapoints (default 5m)
      """

      days_to_request = {
            '1d': 365,
            '5m': 59,
            '1m': 7
        }

      # Pedimos datos hasta hoy
      hoy = dt.datetime.now()

      # cuántos días hacia atrás podemos pedir
      max_dias = days_to_request[interval]
      delta = dt.timedelta(days = max_dias)

      # Llamada a Yahoo: Desde lo más antiguo que podamos hasta hoy
      df = yf.download(tickers = [instrument], interval = interval,
                                 end = hoy, start = hoy - delta)

      # Nos quedamos sólo con la columna que se pidió y reseteamos el índice
      # para que sea una secuencia numérica en lugar del datetime
      df = df.reset_index()

      # Guardamos el resultado en un csv para no tener que volver a pedirlo
      df.to_csv("/tmp/" + instrument + "(" + interval + ").csv")

      return df


    def get_time_series_from_dataframe(dataframe, series_column = "Close", time_column = None):
      """
        A partir de un dataframe, y los nombres de las columnas devuelve dos np.arrays
        uno con el tiempo y el otro con la serie. Si no hay columna de tiempo
        se usa una secuencia empezando en 0

        Keyword arguments:
        dataframe -- dataframe que contiene los datos de donde tomar la serie
        series_column -- nombre de la columna que contiene la serie
        time_column -- nombre de la columna que contiene el tiempo (default None).
                       Si no se pasa, se usa una secuencia numérica 
      """

      series = np.array(dataframe[series_column])
      if time_column is None:
        time = np.array(range(len(series)))
      else:
        time = np.array(dataframe[time_column])

      return time, series


    def split_dataset(time, series, split_time = None):
      """
        Divide el tiempo y la serie en train y test
        Si no se indica en qué punto hacer el corte, se divide 80-20

        Keyword arguments:
        time -- Numpy array que contiene los tiempos de la serie
        series -- Numpy array que contiene los valores de la serie
        split_time -- cantidad de elementos a incluir en el training set
      """

      if split_time is None:
        split_time = len(time) * 10 // 8

      time_train = time[:split_time]
      x_train = series[:split_time]

      time_valid = time[split_time:]
      x_valid = series[split_time:]

      return time_train, x_train, time_valid, x_valid