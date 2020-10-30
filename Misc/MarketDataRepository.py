import os
import os.path
import pandas as pd
from MarketData import MarketData

class MarketDataRepository:
  """
  Este es un repositorio nuestro de datasets.
  Tiene un método get_available_dataset_list que devuelve el listado
  de datasets disponibles.

  Tiene un método det_dataset que devuelve datasets
  filtrados según los criterios de los parámetros.

  En el constructor es conveniente pasarle el path a una carpeta
  que va a ser usada como cache para sólo bajar datasets que no se hayan
  descargado antes y minimizar el acceso a los repos remotos.
  """

  def __init__(self, dataset_cache_url = None):

    # La carpeta pasada por parámetro se usa como cache para
    # no bajar múltiples veces el mismo dataset
    self._dataset_cache_url = dataset_cache_url

    # Por ahora, guradamos los datasets en este diccionario.
    # Más adelante podríamos guardar un csv que sirva de índice y
    # contenga toda esta información.
    self._datasets = {
      ('ICMarkets','AUDJPY'  ,'M1'): '18nvxR0pHkyRasFVoNWxP2O3uyaKZ9a7Y',
      ('ICMarkets','AUDNZD'  ,'M1'): '13P2goZT3CHD5XY4UNU389FVelQD5q5Rv',
      ('ICMarkets','AUDUSD'  ,'M1'): '19LP9zdlbiK8vrSH1jLJpwPgMg0YjDo8f',
      ('ICMarkets','EURCHF'  ,'M1'): '14wJqrQ0OWK-EZJMP7kkNZbXLVtqKFjdz',
      ('ICMarkets','EURGBP'  ,'M1'): '1UsEwryruFtFl9wCKiLSb-VqtV71pKg-3',
      ('ICMarkets','EURJPY'  ,'M1'): '1yih0-CF9Nzb_EaZGJ1CEh9v97_M9nfJl',
      ('ICMarkets','EURUSD'  ,'M1'): '1oExJpDK2E1dZVOPix1xx7FPYQHESxKgZ',
      ('ICMarkets','GBPAUD'  ,'M1'): '1dmJdpatzxOVI3APtRUbXdjEZ3V5Tfhpg',
      ('ICMarkets','GBPCHF'  ,'M1'): '1egC0Z0XNNi5cly3rAKHo_Q3LamrX8lpT',
      ('ICMarkets','GBPJPY'  ,'M1'): '1m5_XZVBWabTp66EP31GwKzjj-VRFNBBK',
      ('ICMarkets','GBPNZD'  ,'M1'): '1qmFGGo1QliDs_XvxVRslu-uWDH3Dba-u',
      ('ICMarkets','GBPUSD'  ,'M1'): '1qO8A48tczgx3fOm30ZObO7qi_-kUd94V',
      ('ICMarkets','NZDUSD'  ,'M1'): '1R6t1KzGoM8scKg3FygaREiSq7pDXPoqB',
      ('ICMarkets','USDCAD'  ,'M1'): '1C2L_zlxcpyw0sZ8nkJLf062M0ABkxlcQ',
      ('ICMarkets','USDCHF'  ,'M1'): '1CbfASN1BxERT5xam77gLGzAcDRdurZqJ',
      ('ICMarkets','USDJPY'  ,'M1'): '1sri_L9tGTMXyNi7FfXoakR7azzZjthzr',
      ('ICMarkets','USDMXN'  ,'M1'): '1wh2So03KCO6lFE1Zz2eNr0xqaocOoHW6',
      ('ICMarkets','XAGUSD'  ,'M1'): '17067jME_ZxK-qNJYWaaMbDK4wRybd-ut',
      ('ICMarkets','XAUUSD'  ,'M1'): '1FQw5oLLGBkV0I4A5RuHGOmZ1GhEgV_CG',
      ('ICMarkets','XCUUSD'  ,'M1'): '1CcZhkCVoh5n2eFMd2kwaxTuPf9wCI7Ar',
      ('ICMarkets','^ESP35'  ,'M1'): '1wFQyCXnyoI8D6BmFubRHQrkPPsN6Tv7H',
      ('ICMarkets','^EUSTX50','M1'): '1F9hKMK7HLlpZmdPyEC33lSsZHdbQKMvR',
      ('ICMarkets','^JPN225' ,'M1'): '1tWh5jYEzt7zjUe_nDLFFyWpEpQa3n4jm',
      ('ICMarkets','^UK100'  ,'M1'): '14n9TiiyIg611X3DjRpSO9HY7z-efj2tn',
      ('ICMarkets','^US500'  ,'M1'): '17cT7dOPvxnlYkoPhzm2wBgVdydugvhMF'
    }

  def get_dataset(self, symbol, frequency = 'M1', start_date = '2016-09-01', rows = None):
    """
    Devuelve un dataset filtrado según los parámetros.
    Para obtener los posibles valores que se le pueden pasar, llamar al método
    get_available_dataset_list.

    Argumentos:
    symbol: símbolo para el cual se requiere la información.
    frequency: por ahora sólo puede ser 'M1', luego podemos armar velas
               de frecuencias menores.
    start_date: fecha desde la cual se requiere la información.
    rows: cantidad de filas a pedir. Se recomienda no usar el dataset
          completo porque tiene millones de filas
    """

    # Esto va a ser configurable después. Por ahora es siempre el mismo valor
    source = 'ICMarkets'

    # Armo la clave para ir a buscar al diccionario
    key = (source, symbol, frequency)

    # Si la clave no está, no puedo seguir
    assert key in self._datasets, "No se encuentra el dataset"

    # Obtengo el id del archivo desde el diccionario
    csv_file = self._datasets[key]

    # Obtengo el archivo usando un método privado de la clase
    data = self._get_file(csv_file)

    # Me quedo con las filas desde start_data en adelante
    data = data.loc[start_date:]

    # Chequeo que haya datos antes de devolverlos
    assert rows < data.shape[0], "No hay suficientes datos para devolver"

    # Si se pidió una cantidad de filas, me quedo con la cantidad solicitada
    if rows:
      data = data.head(rows)

    # data tiene ahora las primeras 'rows' filas desde 'start_date' en adelante
    # MarketData encapsula el dataset y toda su metadata
    return MarketData(symbol, frequency, start_date, rows, data)


  def get_available_dataset_list(self):
    """
    Devuelve el listado de (símbolo, frecuencia) disponibles.
    """

    # La key del diccionario está formada por source, symbol y frequency,
    # pero sólo devolvemos el símbolo y la frecuencia
    return [(symbol, frequency)
            for source, symbol, frequency
            in self._datasets.keys()]



  def _get_file(self, csv_file):
    """
    Este método es PRIVADO. No llamalo desde afuera.
    Devuelve el archivo solicitado teniendo en cuenta la cache local.
    Si hay una carpeta de cache configurada, primero chequea ahí.
    Si no está, busca el archivo en drive.
    Si hay carpeta de cache configurada, guarda el archivo ahí.
    """

    # Armo el nombre del archivo dentro de la carpeta para cache de archivos
    if self._dataset_cache_url:

      # Me aseguro de que exista la carpeta
      if not os.path.exists(self._dataset_cache_url):
        os.makedirs(self._dataset_cache_url)

      cached_file_name = self._dataset_cache_url + '/' + csv_file + '.csv'

    # Si tengo cache y además un archivo con el nombre correspondiente
    if self._dataset_cache_url and os.path.isfile(cached_file_name):

      # Leo el archivo desde esa carpeta local
      data = pd.read_csv(cached_file_name, index_col = "Datetime")

    else:
      # Si no, lo leo de drive
      link = "https://drive.google.com/uc?id=" + csv_file
      data = pd.read_csv(link, index_col = "Datetime")

    # Si tengo cache pero aun no se guardó este archivo
    if self._dataset_cache_url and not os.path.isfile(cached_file_name):

      # Lo guardo en el mismo lugar donde antes chequeé si existía
      data.to_csv(cached_file_name)

    return data