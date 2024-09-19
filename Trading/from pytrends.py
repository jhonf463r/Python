from pytrends.request import TrendReq
import pandas as pd
import time

# Inicializa pytrends
pytrends = TrendReq(hl='es', tz=360)

# Define las palabras clave y el rango de tiempo
kw_list = ['AMZN', 'NVDA', 'BABA', 'GOOGL', 'MSFT', 'AAPL']
timeframe = '2022-08-01 2024-08-06'
geo = ''  # País vacío para todo el mundo
gprop = ''  # Vacío para búsquedas en la web

# Función para manejar la solicitud con reintentos
def fetch_trends(pytrends, kw_list, timeframe, geo, gprop, retries=3):
    for _ in range(retries):
        try:
            pytrends.build_payload(kw_list, timeframe=timeframe, geo=geo, gprop=gprop)
            return pytrends.interest_over_time()
        except Exception as e:
            print(f"Error: {e}. Reintentando...")
            time.sleep(5)  # Esperar 5 segundos antes de reintentar
    raise Exception("Failed to fetch trends data after multiple retries.")

# Dividir la lista de palabras clave en partes manejables
chunked_kw_list = [kw_list[i:i + 3] for i in range(0, len(kw_list), 3)]

# Recopilar todos los datos
all_data = pd.DataFrame()

for chunk in chunked_kw_list:
    interest_over_time = fetch_trends(pytrends, chunk, timeframe, geo, gprop)
    all_data = pd.concat([all_data, interest_over_time], axis=1)

# Eliminar la columna 'isPartial' duplicada
if 'isPartial' in all_data.columns:
    all_data = all_data.loc[:, ~all_data.columns.duplicated()]

# Guarda los datos en un archivo CSV
all_data.to_csv('google_trends_data.csv')

print("Datos descargados y guardados en 'google_trends_data.csv'")
