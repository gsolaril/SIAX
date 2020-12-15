from SIAX.PreProcessing.KeepColumnsPreProcessor import KeepColumnsPreProcessor

class DiffPreProcessor(KeepColumnsPreProcessor):
  """
  This PreProcessor inherits from `KeepColumnsPreProcessor`
  It calculates the difference of a dataset.
  If S is the original dataset, and D is the resulting dataset:
  D[n] = S[n+1] - S[n], for example:  D[0] = S[1] - S[0]
  """

  def __init__(self):
    super().__init__()
    self._steps.extend([self._diff])
    self.extra_rows += 1

  def _diff(self, df):
    return df.diff()[1:]