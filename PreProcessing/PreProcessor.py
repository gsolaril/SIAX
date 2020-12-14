class PreProcessor:
  """
  This class has a __call__ method that applies transformations to a dataframe
  and then returns it transformed.
  """
  def __init__(self):
    self._steps = []

  def __call__(self, df):
    for step in self._steps:
      df = step(df)
    
    return df

  def _append_step(self, step):
    self._steps.append(step)