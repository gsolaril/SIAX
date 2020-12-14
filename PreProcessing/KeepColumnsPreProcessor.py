from SIAX.PreProcessing.PreProcessor import PreProcessor

class KeepColumnsPreProcessor(PreProcessor):
  """
  This Pre Processor resets the index of the dataframe and only keeps certain columns.
  By default it keeps 'Open','Low', 'High', 'Close', but a different list can be passed in the constructor
  """

  def __init__(self, columns_to_keep = ['Open','Low', 'High', 'Close']):
    super().__init__()
    self._columns_to_keep = columns_to_keep
    self._steps.extend([self._reset_index, self._keep_only_required_columns])

  def _reset_index(self, df):
    return df.reset_index()

  def _keep_only_required_columns(self, df):
    return df[self._columns_to_keep]