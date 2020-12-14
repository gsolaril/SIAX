import numpy as np
import tensorflow as tf
from keras.models import model_from_json
from os import path

from SIAX.NeuralNetworks.ModelConfiguration import ModelConfiguration

class ModelBase():
  """
  Base class for all neural network based models.
  It's only required to override the `build_model` method.
  """

  def __init__(self, window_size, model_configuration=ModelConfiguration()):
    super().__init__()
    self.window_size = window_size
    self.config = model_configuration
    self.model = self.build_model()
    self.model.compile(loss=self.config.loss,
                  optimizer=self.config.optimizer,
                  metrics=self.config.metrics)

  def build_model(self):
    return None

  def __call__(self, inputs):
    return self.call(inputs)

  def call(self, inputs):
    return self.model(inputs)
  
  def evaluate(self, inputs_labels):
    return self.model.evaluate(inputs_labels)

  def train(self, train_data, validation_data = None):

    if validation_data:
      self.history = self.model.fit(train_data, epochs=self.config.max_epochs,
                          validation_data=validation_data,
                          callbacks=self.config.callbacks,
                          batch_size=self.config.batch_size)
    else:      
      self.history = self.model.fit(train_data, epochs=self.config.max_epochs,
                          callbacks=self.config.callbacks,
                          batch_size=self.config.batch_size)

    return self.history

  def save_model(self, directory = '.'):

    # Serializo el modelo en un JSON
    model_json = self.model.to_json()

    # Guardo el modelo en formato JSON
    with open(path.join(directory, str(type(self).__name__) + ".json"), "w") as json_file:
        json_file.write(model_json)

    # Guardo los pesos en un archivo .h5
    self.model.save_weights(path.join(directory, str(type(self).__name__) + '.h5'))