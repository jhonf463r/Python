###############################################################################
#                                                                             #
#                          Adquisición de Datos de Google Trends              #
#                                                                             #
#  Objetivo: Este script recupera datos diarios de interés de búsqueda para    #
#  empresas tecnológicas clave: Amazon (AMZN), NVIDIA (NVDA), Alibaba (BABA),  #
#  Google (GOOGL), Microsoft (MSFT) y Apple (AAPL) desde Google Trends,       #
#  abarcando desde el 1 de agosto de 2022 hasta la fecha actual.             #
#                                                                             #
#  Metodología: El interés se cuantifica en una escala de 0 a 100, reflejando  #
#  la popularidad relativa de las búsquedas a lo largo del tiempo. Estos datos #
#  pueden utilizarse para fines analíticos, incluyendo la correlación con      #
#  tendencias de mercado y rendimiento de acciones. Los resultados se exportan  #
#  a un archivo CSV para su análisis y visualización posterior.               #
#                                                                             #
###############################################################################



from pytrends.request import TrendReq
import pandas as pd
import time
from datetime import datetime

# Inicializa pytrends para interactuar con Google Trends
pytrends = TrendReq(hl='es', tz=360)

# Define las palabras clave (empresas) y el rango de fechas
kw_list = ['AMZN', 'NVDA', 'BABA', 'GOOGL', 'MSFT', 'AAPL']
start_date = '2022-08-01'  # Fecha de inicio
end_date = datetime.now().strftime('%Y-%m-%d')  # Fecha actual
timeframe = f'{start_date} {end_date}'  # Rango de tiempo desde el 1 de agosto de 2022 hasta hoy
geo = ''  # Para todo el mundo
gprop = ''  # Para búsquedas en la web

# Función que intenta obtener datos de Google Trends con varios reintentos en caso de fallo
def fetch_trends(pytrends, kw_list, timeframe, geo, gprop, retries=3):
    for _ in range(retries):
        try:
            pytrends.build_payload(kw_list, timeframe=timeframe, geo=geo, gprop=gprop)  # Solicita los datos
            return pytrends.interest_over_time()  # Retorna el interés a lo largo del tiempo
        except Exception as e:
            print(f"Error: {e}. Reintentando...")
            time.sleep(5)  # Espera 5 segundos antes de reintentar
    raise Exception("Failed to fetch trends data after multiple retries.")  # Error si no se puede obtener datos tras reintentos

# Divide la lista de palabras clave en partes más pequeñas para manejar mejor la solicitud
chunked_kw_list = [kw_list[i:i + 3] for i in range(0, len(kw_list), 3)]

# Recopila todos los datos de las solicitudes por partes
all_data = pd.DataFrame()

# Itera por cada parte de la lista de palabras clave y junta los datos en un solo DataFrame
for chunk in chunked_kw_list:
    interest_over_time = fetch_trends(pytrends, chunk, timeframe, geo, gprop)
    all_data = pd.concat([all_data, interest_over_time], axis=1)

# Elimina la columna 'isPartial' duplicada (indicador de si los datos son parciales)
if 'isPartial' in all_data.columns:
    all_data = all_data.loc[:, ~all_data.columns.duplicated()]

# Guarda los datos obtenidos en un archivo CSV
all_data.to_csv('google_trends_data.csv')

print("Datos descargados y guardados en 'google_trends_data.csv'")
