import os
import numpy as np
import pandas as pd
import keras as k
import datetime as dt
import matplotlib.pyplot as plt
import csv
import tensorflow as tf

from SIAX.PreProcessing.PreProcessor import PreProcessor

class NeuralNetworkStrategy:

  def __init__(self, model, pre_processor = PreProcessor(), OHLC = "Close"):
    """
      Se puede heredar de esta clase y sobreescribirle cualquiera de los
      siguientes métodos:
    
      * calculate_type_of_operation: Qué operación hacer
      * calculate_stop_loss: Cómo setear el Stop Loss
      * calculate_take_profit: Cómo setear el Take Profit
      * calculate_indicators: Cómo obtener indicadores
    """

    self.model = model
    self.minRows = model.window_size + pre_processor.extra_rows
    self.Indicators = []
    self.OHLC = OHLC
    self.pre_processor = pre_processor


  def call(self, rows):
    return self.__call__(rows)

  def __call__(self, rows):

    OT = OP = Type = Lot = SL = TP = None  ## Default: None.

    processed_rows = self._pre_process_rows(rows)

    prediction = self.model.call(processed_rows)

    Type = self.calculate_type_of_operation(prediction)

    if Type:                        # Si compro o vendo...
      OT, Lot = rows.index[-1], 1   # Opening Time y Lote
      OP = rows["Close"].iloc[-1]   # La operación se ejecuta al cierre de vela.

      SL = self.calculate_stop_loss(rows, Type, prediction)

      TP = self.calculate_take_profit(rows, Type, prediction, SL, OP)

    Indicators = self.calculate_indicators(rows, Type, prediction, SL, OP, TP)

    Signal = {"OT": OT, "OP": OP, "Type": Type, "Size": Lot, "SL": SL, "TP": TP}

    return Indicators, Signal

  def _pre_process_rows(self, rows):
    """
    Este método no se debería sobreescribir. Recibe las rows y se le aplica
    el pre procesamiento que se recibió en el constructor
    """
    # Llamo al pre procesador
    processed_rows = self.pre_processor(rows)

    # Convierto la salida en un array de numpy
    processed_rows = np.array(processed_rows)

    # Le agrego una dimensión al principio porque sólo quiero una predicción
    # y no un batch completo
    return tf.expand_dims(processed_rows,0)

  def calculate_type_of_operation(self, prediction):
    """
    En base a la predicción, devuelve el tipo de operación a realizar.
    1 para comprar. -1 para vender. 0 para no hacer nada
    """
    
    t = 1 if prediction > 0 else -1 if prediction < -0.1 else None

    return t

  def calculate_stop_loss(self, rows, Type, prediction):
    """
    Calcula el Stop Loss en base a alguna estrategia.
    Este método se debería sobreescribir para definir otra estrategia
    para el cálculo del Stop Loss
    """
    
    highest = max(rows["High"])
    lowest = min(rows["Low"])

    SL = 0

    if Type > 0:
      SL = lowest - np.abs(lowest) * 0.001
    else:
      SL = highest + np.abs(highest) * 0.001

    return SL

  def calculate_take_profit(self, rows, Type, prediction, SL, OP):
    """
    Calcula el Stop Loss en base a alguna estrategia.
    Este método se debería sobreescribir para definir otra estrategia
    para el cálculo del Stop Loss
    """

    # Copio la del Opening Price al Stop Loss y la multiplico por 2.
    TP = OP + Type * abs(OP - SL) * 2

    return TP

  def calculate_indicators(self, rows, Type, prediction, SL, OP, TP):
    """
    A partir de todos los valores relevantes de la operación calcula
    los indicadores necesarios.
    Este método se debería sobreescribir porque la implementación por
    defecto no calcula ningún indicador
    """
    return {}