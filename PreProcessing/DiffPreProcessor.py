from SIAX.PreProcessing.PreProcessor import PreProcessor

class DiffPreProcessor(PreProcessor):
  """
  This Pre Processor calculates the difference of a dataset.
  If S is the original dataset, and D is the resulting dataset:
  D[n] = S[n+1] - S[n], for example:  D[0] = S[1] - S[0]
  """

  def __init__(self):
    super().__init__()
    self._steps.extend([self._reset_index, self._drop_datetime, self._zero_volume, self._diff])

  def _reset_index(self, df):
    return df.reset_index()

  def _drop_datetime(self, df):
    return df.drop(columns=["Datetime"])

  def _zero_volume(self, df):
    df['Vol'] = 0
    return df

  def _diff(self, df):
    return df.diff()[1:]