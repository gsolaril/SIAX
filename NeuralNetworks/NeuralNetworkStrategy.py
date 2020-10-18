import os
import numpy as np
import pandas as pd
import keras as k
import datetime as dt
import matplotlib.pyplot as plt
import csv
import tensorflow as tf

class NeuralNetworkStrategy:

  def __init__(self, model, OHLC = "Close"):
    """
      Se puede heredar de esta clase y sobreescribirle cualquiera de los
      siguientes métodos:
    
      * get_series_to_forecast: Cómo extraer la serie a partir de una Row.
      * calculate_type_of_operation: Qué operación hacer
      * calculate_stop_loss: Cómo setear el Stop Loss
      * calculate_take_profit: Cómo setear el Take Profit
      * calculate_indicators: Cómo obtener indicadores
    """

    self.model = model
    self.minRows = model.window_size + 2
    self.Indicators = []
    self.OHLC = OHLC


  def call(self, Rows):

    OT = OP = Type = Lot = SL = TP = None  ## Default: None.

    series_to_forecast = get_series_to_forecast(Rows)

    prediction = self.model.predict(series_to_forecast)[0]

    Type = calculate_type_of_operation(prediction)

    if Type:                                                 # Si compro o vendo...
      OT, Lot = Rows.index[-1], 1                            # Opening Time y Lote
      OP = Rows["Close"].iloc[-1]                            # La operación se ejecuta al cierre de vela.

      SL = calculate_stop_loss(Rows, Type, prediction)

      TP = calculate_take_profit(Rows, Type, prediction, SL, OP)

    Indicators = calculate_indicators(Rows, Type, prediction, SL, OP, TP)

    Signal = {"OT": OT, "OP": OP, "Type": Type, "Size": Lot, "SL": SL, "TP": TP}

    return Indicators, Signal


  def get_series_to_forecast(self, Rows):
    """
    A partir de las Rows que recibe para hacer la predicción,
    devuelve la serie de datos que le va a pasar al modelo.
    
    Keyword arguments:
    Rows -- Las filas crudas del dataset como las recibe el método call
    
    returns -- Los valores de la serie de tiempo extraidos de las Rows
    """
  
    Calc = Rows[self.OHLC]                 ## Tomo la columna que quiero usar
    series_to_forecast = Calc.to_numpy().T ## La columna del df convertida en serie
    
    return series_to_forecast


  def calculate_type_of_operation(self, prediction):
    """
    En base a la predicción, devuelve el tipo de operación a realizar.
    1 para comprar. -1 para vender. 0 para no hacer nada
    """
    
    t = 1 if prediction > 0 else -1 if prediction < -0.1 else 0

    return t

  def calculate_stop_loss(self, Rows, Type, prediction):
    """
    Calcula el Stop Loss en base a alguna estrategia.
    Este método se debería sobreescribir para definir otra estrategia
    para el cálculo del Stop Loss
    """
    
    highest = max(Rows["High"])
    lowest = min(Rows["Low"])

    SL = 0

    if Type > 0:
      SL = lowest - np.abs(lowst) * 0.01
    else:
      SL = highest + np.abs(highest) * 0.01

    return SL

  def calculate_take_profit(self, Rows, Type, prediction, SL, OP):
    """
    Calcula el Stop Loss en base a alguna estrategia.
    Este método se debería sobreescribir para definir otra estrategia
    para el cálculo del Stop Loss
    """

    # Copio la del Opening Price al Stop Loss y la multiplico por 2.
    TP = OP + Type * abs(OP - SL) * 2

    return TP

  def calculate_indicators(self, Rows, Type, prediction, SL, OP, TP):
    """
    A partir de todos los valores relevantes de la operación calcula
    los indicadores necesarios.
    Este método se debería sobreescribir porque la implementación por
    defecto no calcula ningún indicador
    """
    return {}