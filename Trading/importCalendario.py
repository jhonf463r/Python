import requests
from bs4 import BeautifulSoup
import pandas as pd

# URL del sitio web de eventos
url = 'https://example.com/events'  # Reemplaza con la URL real

# Obtener el contenido de la página
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

# Parsear los eventos
events = []
for event in soup.find_all('div', class_='event'):
    date = event.find('span', class_='date').text
    location = event.find('span', class_='location').text
    duration = event.find('span', class_='duration').text
    events.append({'date': date, 'location': location, 'duration': duration})

# Crear un DataFrame y guardar los datos en un archivo CSV
events_df = pd.DataFrame(events)
events_df.to_csv('scraped_events.csv', index=False)

print("Datos de eventos raspados y guardados en 'scraped_events.csv'")
