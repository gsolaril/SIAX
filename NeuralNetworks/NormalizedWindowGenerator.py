class NormalizedWindowGenerator(WindowGenerator):
  """
  A `WindowGenerator` that normalizes the data before returning it.
  The mean and standard deviation used to normalize are stored in the
  `mean` and `std` attributes.
  """

  def __init__(self, input_width, label_width, shift, df, label_columns=None, batch_size=32):
    super().__init__(input_width, label_width, shift, df, label_columns,batch_size)

    # Normalize all the data based on the train distribution
    normalized = DataFrameProcessing.normalize_data(
        self.train_df, self.val_df, self.test_df)

    self.train_df, self.val_df, self.test_df, self.mean, self.std = normalized