import os
import numpy as np
import pandas as pd
import yfinance as yf
import keras as k
import datetime as dt
import matplotlib.pyplot as plt
import csv
import tensorflow as tf
from keras.models import model_from_json
from os import path

class WindowBasedModel:

  def __init__(self, window_size = 50, epochs = 500, batch_size = 100, transform_series = None):

    self.window_size = window_size
    self.batch_size = batch_size
    self.epochs = epochs
    self.shuffle_buffer = 1000
    self.random_seed = 51
    self.momentum = 0.9
    self.metrics = ["mae", "mse"]
    self.transform_series = transform_series

    
  def train(self, train_series):
    """
      Entrena el modelo con la serie del parámetro.
    """
    if self.transform_series:
      train_series = self.transform_series(train_series)

    train_set = self.to_windowed_dataset(train_series)
    self.build_model()
    self.reset_backend()
    self.history = self.model.fit(train_set,epochs=self.epochs)


  def predict(self, test_series):
    if self.transform_series:
      test_series = self.transform_series(test_series)

    forecast = self._model_forecast(test_series)

    return forecast[:-1, -1, 0]


  def describe(self):
    return "Esta usa un tamaño de ventana {0} y un LR: {1}".format(self.window_size, self.lr)

  def to_windowed_dataset(self, series):
    """
      Divide la serie en ventanas. Toma window_size elementos
      Y les asigna como label el siguiente elemento

      Keyword arguments:
      series -- Numpy array que contiene los valores de la serie
      window_size -- tamaño de la ventana de datos a considerar en la predicción
      batch_size -- cantidad de casos a procesar por paso
      shuffle_buffer -- tamaño del buffer que se usa para mezclar ejemplos
    """

    # Expande una dimensión
    series = tf.expand_dims(series, axis=-1)

    # Divide a la serie en rebanadas de un elemento cada una
    ds = tf.data.Dataset.from_tensor_slices(series)

    # Crea ventanas con window_size + 1 elementos.
    # shift = 1: En cada paso se mueve un elemento a la derecha
    # drop_reminder = True: cuando llega al final de la serie y no hay
    #                       suficientes elementos para completar la ventana,
    #                       corta en lugar de tener ventanas más chicas.
    ds = ds.window(self.window_size + 1, shift = 1, drop_remainder=True)
    
    # Convierte las ventanas en una lista de datasets
    ds = ds.flat_map(lambda w: w.batch(self.window_size + 1))
    
    # Mezcla los datasets creados en el paso anterior
    ds = ds.shuffle(self.shuffle_buffer)

    # Convierte cada ventana de tamaño wondow_size + 1 en una tupla
    # de la forma (array tamaño window_size, array_tamaño 1)
    # es decir: (datos, labels), es decir: (x, y)
    ds = ds.map(lambda w: (w[:-1], w[1:]))

    # Devuelve los datasets (x, y) en batches de tamaño batch_size
    return ds.batch(self.batch_size).prefetch(1)


  def reset_backend(self):
    """
      Esta función limpia la sesión de keras y resetea el random para que
      distintas ejecuciones den resultados similares (o iguales)
    """
    tf.keras.backend.clear_session()
    tf.random.set_seed(self.random_seed)
    np.random.seed(self.random_seed)


  def _model_forecast(self, series):
    """
      Para cada window_size elementos de series predice el siguiente valor
      utilizando el modelo "model"

      Keyword arguments:
      model -- Modelo a usar para predecir
      series -- Numpy array que contiene los valores de la serie
      window_size -- tamaño de la ventana de datos a considerar en la predicción
    """

    series = tf.expand_dims(series, axis=-1)

    # Como en windowed_dataset dividimos la serie en rebanadas o slices
    ds = tf.data.Dataset.from_tensor_slices(series)

    # Como en windowed_dataset agrupamos las slices en ventanas
    # pero esta vez de tamaño "window_size" porque no tenemos labels
    ds = ds.window(self.window_size, shift = 1, drop_remainder=True)

    # Creamos pequeños datasets con elementos consecutivos de tamaño window_size
    ds = ds.flat_map(lambda w: w.batch(self.window_size))

    # Creamos batches de self.batch_size datasets
    ds = ds.batch(self.batch_size).prefetch(1)

    # Y le pedimos al modelo que prediga
    forecast = self.model.predict(ds)

    # Finalmente devolvemos la predicción
    return forecast


  def save_model(self, directory = '.'):

    # Serializo el modelo en un JSON
    model_json = self.model.to_json()

    # Guardo el modelo en formato JSON
    with open(path.join(directory, self.get_weights_name() + ".json"), "w") as json_file:
        json_file.write(model_json)

    # Guardo los pesos en un archivo .h5
    self.model.save_weights(path.join(directory, self.get_weights_name() + '.h5'))