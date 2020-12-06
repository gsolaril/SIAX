from SIAX.NeuralNetworks.WindowGenerator import WindowGenerator
from SIAX.NeuralNetworks.NormalizedWindowGenerator import NormalizedWindowGenerator

class WindowGeneratorFactory:

  @staticmethod
  def build_multi_input(df, label_columns, input_window_width=5, label_width=24, batch_size=32):
    """
    Builds a WindowGenerator to be used in a convolutional network
    """
    # The input width needs to account for the input window size
    input_width = label_width + input_window_width - 1

    window_generator = NormalizedWindowGenerator(
      input_width=input_width,
      label_width=label_width,
      df = df,
      shift=1,
      label_columns=label_columns,
      batch_size = batch_size)

    return window_generator

  @staticmethod
  def build_multi_input_diff(df, label_columns, input_window_width = 5, label_width = 24, batch_size=32):
    """
    Builds a NormalizedWindowGenerator to be used in a convolutional network but takes
    the difference of a series instead of the series.
    The input would be D instead of S, where D[n] = S[n+1] - S[n]
    For example: D[0] = S[1] - S[0] and D[1] = S[2] - S[1]
    """
    # The input width needs to account for the input window size
    input_width = label_width + input_window_width - 1

    df = df.diff()[1:]

    window_generator = WindowGenerator(
      input_width=input_width,
      label_width=label_width,
      df = df,
      shift=1,
      label_columns=label_columns,
      batch_size = batch_size)
    
    return window_generator

  @staticmethod
  def build_regular(df, label_columns, label_width = 24):
    """
    Builds a NormalizedWindowGenerator that has the same with for the label
    and the input, and a shift of 1.
    """
    # The input width is the same as the label width
    input_width = label_width

    window_generator = NormalizedWindowGenerator(
      input_width=input_width, label_width=label_width, shift=1,
      df = df,
      label_columns=label_columns)
    
    return window_generator