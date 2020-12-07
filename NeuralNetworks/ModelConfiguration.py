import tensorflow as tf

class ModelConfiguration:

  def __init__(self,
               optimizer = tf.optimizers.Adam(0.001),
               max_epochs = 500,
               batch_size = 32,
               loss = tf.keras.losses.MeanAbsoluteError(),
               metrics = [tf.metrics.MeanSquaredError()],
               callbacks = tf.keras.callbacks.EarlyStopping(monitor='loss', mode='min', patience=50)):

    self.optimizer = optimizer
    self.max_epochs = max_epochs
    self.loss = loss
    self.metrics = metrics
    self.callbacks = callbacks