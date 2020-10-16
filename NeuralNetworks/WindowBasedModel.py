class WindowBasedModel:

  def __init__(self, window_size = 50, epochs = 500, batch_size = 100):

    self.window_size = window_size
    self.batch_size = batch_size
    self.epochs = epochs
    self.shuffle_buffer = 1000
    self.random_seed = 51
    self.momentum = 0.9
    self.metrics = ["mae", "mse"]

    
  def train(self, train_series):
    """
      Entrena el modelo con la serie del parámetro.
    """

    diff_series = self.get_difference_series(train_series)
    train_set = self.to_windowed_dataset(diff_series)
    self.build_model()
    self.reset_backend()
    self.history = self.model.fit(train_set,epochs=self.epochs)


  def predict(self, test_series):
    diff_series = self.get_difference_series(test_series)
    forecast = self.model_forecast(diff_series)

    return forecast[:-1, -1, 0]


  def describe(self):
    return "Esta usa un tamaño de ventana {0} y un LR: {1}".format(self.window_size, self.lr)


  def get_percentage_difference_series(self, series):
    """
      A partir de una serie original S con distintos valores en cada t
      devuelve una serie D con una longitud de una unidad menos
      donde D[t] = ( S[t] - S[t-1] ) / S[t-1]
    
      Keyword arguments:
      series -- serie a la que se le pretende calcular la diferencia
    """
    
    # A cada elemento se le resta el que está en la posición anterior
    # y se lo divide por el valor anterior.
    # D[0] = ( S[1] - S[0] ) / S[0]
    # D[1] = ( S[2] - S[1] ) / S[1]
    diff = (series[1:] - series[:-1]) / series[:-1]
    
    # Finalmente le agregamos un 0 al principio porque el primer día no sabemos
    # cuánto aumentó y no calculamos la diferencia
    return diff


  def get_difference_series(self, series):
    """
      A partir de una serie original S con distintos valores en cada t
      devuelve una serie D con una longitud de una unidad menos
      donde D[t] = S[t] - S[t-1]

      Keyword arguments:
      series -- serie a la que se le pretende calcular la diferencia
    """

    # A cada elemento se le resta el que está en la posición anterior.
    # D[0] = S[1] - S[0]
    # D[1] = S[2] - S[1]
    diff = series[1:] - series[:-1]

    # Finalmente le agregamos un 0 al principio porque el primer día no sabemos
    # cuánto aumentó y no calculamos la diferencia
    return diff


  def to_windowed_dataset(self, series):
    """
      Divide la serie en ventanas. Toma window_size elementos
      Y les asigna como label el siguiente elemento

      Keyword arguments:
      series -- Numpy array que contiene los valores de la serie
      window_size -- tamaño de la ventana de datos a considerar en la predicción
      batch_size -- cantidad de casos a procesar por paso
      shuffle_buffer -- tamaño del buffer que se usa para mezclar ejemplos
    """

    # Expande una dimensión
    series = tf.expand_dims(series, axis=-1)

    # Divide a la serie en rebanadas de un elemento cada una
    ds = tf.data.Dataset.from_tensor_slices(series)

    # Crea ventanas con window_size + 1 elementos.
    # shift = 1: En cada paso se mueve un elemento a la derecha
    # drop_reminder = True: cuando llega al final de la serie y no hay
    #                       suficientes elementos para completar la ventana,
    #                       corta en lugar de tener ventanas más chicas.
    ds = ds.window(self.window_size + 1, shift = 1, drop_remainder=True)
    
    # Convierte las ventanas en una lista de datasets
    ds = ds.flat_map(lambda w: w.batch(self.window_size + 1))
    
    # Mezcla los datasets creados en el paso anterior
    ds = ds.shuffle(self.shuffle_buffer)

    # Convierte cada ventana de tamaño wondow_size + 1 en una tupla
    # de la forma (array tamaño window_size, array_tamaño 1)
    # es decir: (datos, labels), es decir: (x, y)
    ds = ds.map(lambda w: (w[:-1], w[1:]))

    # Devuelve los datasets (x, y) en batches de tamaño batch_size
    return ds.batch(self.batch_size).prefetch(1)


  def reset_backend(self):
    """
      Esta función limpia la sesión de keras y resetea el random para que
      distintas ejecuciones den resultados similares (o iguales)
    """
    tf.keras.backend.clear_session()
    tf.random.set_seed(self.random_seed)
    np.random.seed(self.random_seed)


  def model_forecast(self, series):
    """
      Para cada window_size elementos de series predice el siguiente valor
      utilizando el modelo "model"

      Keyword arguments:
      model -- Modelo a usar para predecir
      series -- Numpy array que contiene los valores de la serie
      window_size -- tamaño de la ventana de datos a considerar en la predicción
    """

    series = tf.expand_dims(series, axis=-1)

    # Como en windowed_dataset dividimos la serie en rebanadas o slices
    ds = tf.data.Dataset.from_tensor_slices(series)

    # Como en windowed_dataset agrupamos las slices en ventanas
    # pero esta vez de tamaño "window_size" porque no tenemos labels
    ds = ds.window(self.window_size, shift = 1, drop_remainder=True)

    # Creamos pequeños datasets con elementos consecutivos de tamaño window_size
    ds = ds.flat_map(lambda w: w.batch(self.window_size))

    # Creamos batches de self.batch_size datasets
    ds = ds.batch(self.batch_size).prefetch(1)

    # Y le pedimos al modelo que prediga
    forecast = self.model.predict(ds)

    # Finalmente devolvemos la predicción
    return forecast


  def save_model(self):
    self.model.save_weights('/tmp/' + self.get_weights_name() + '.h5')