import numpy as np
import pandas as pd
import datetime as dt
import tensorflow as tf

class DataFrameProcessing:

  def __init__(self, val_percent = None, test_percent = None):
    self.val_percent = val_percent
    self.test_percent = test_percent

  @staticmethod
  def no_split():
    return DataFrameProcessing()

  def take_one_every_n(self, df, n):
    """
    Starting from n - 1 index, take every nth item.
    """
    return df[n-1::n]

  def extract_datetime_column(self, df, datetime_column_name = 'Date Time', format='%d.%m.%Y %H:%M:%S'):
    return pd.to_datetime(df.pop(datetime_column_name), format=format)

  def datetime_to_timestamp(self, date_time):
    """
    From a datetime DataFrame column, returns a column of the same lenght
    but containing the corresponding timestamp values instead
    """
    return date_time.map(dt.datetime.timestamp)

  def split_data(self, df):
    """
    Splits the dataframe df in train/validation/test based on the
    provided percentages. It returns the three of them.

    Returns: train_df, val_df, test_df
    """
    n = len(df)

    if self.val_percent == None:
      train_df = df.copy()
      val_df = None
      test_df = None

    else:
      train_df = df[0:int(n*self.val_percent)].copy()

      if self.test_percent:
        val_df = df[int(n*self.val_percent):int(n*self.test_percent)].copy()
        test_df = df[int(n*self.test_percent):].copy()

      else:
        val_df = df[int(n*self.val_percent):].copy()
        test_df = None

    return train_df, val_df, test_df

  def normalize_data(self, train_df, val_df, test_df):
    """
    Normalizes the three dataframes based on train's mean and std.

    Returns: train_df, val_df, test_df, train_mean, train_std
    """
    train_mean = train_df.mean()
    train_std = train_df.std()

    train_df = (train_df - train_mean) / train_std
    val_df = (val_df - train_mean) / train_std
    test_df = (test_df - train_mean) / train_std

    return train_df, val_df, test_df, train_mean, train_std

  def fourier(self, column, step = 24*365.2524):
    """
    Based on a dataframe column and a step size, it returns the fourier transform.
    Returns: f_per_step (x values), fft (y values)
    """
    fft = tf.signal.rfft(column)
    f_per_dataset = np.arange(0, len(fft))

    n_samples_h = len(column)
    steps_per_dataset = n_samples_h / step

    f_per_step = f_per_dataset/steps_per_dataset

    return f_per_step, fft