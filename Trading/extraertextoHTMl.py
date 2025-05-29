from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os

def extract_text_from_html(file_path):
    # Verifica si el archivo existe
    if not os.path.isfile(file_path):
        print(f"El archivo {file_path} no se encontró.")
        return

    # Abre el archivo HTML
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

        # Extrae el título
        title = soup.find('title')
        if title:
            print("Título:")
            print(title.get_text(strip=True))
        else:
            print("No se encontró el título.")
        
        # Extrae la descripción
        meta_description = soup.find('meta', attrs={'name': 'description'})
        if meta_description:
            description = meta_description.get('content', '').strip()
            print("Descripción:")
            print(description)
        else:
            print("No se encontró la descripción.")

        # Extrae el cuerpo de la noticia
        body = soup.find('body')
        if body:
            # Busca el contenedor del cuerpo de la noticia
            news_body = body.find('div', class_='press-release__body')  # Cambia la clase según el HTML real
            if news_body:
                text = news_body.get_text(strip=True)
                print("Texto extraído:")
                print(text)
                
                # Análisis de sentimiento con VADER
                analyzer = SentimentIntensityAnalyzer()
                sentiment_score = analyzer.polarity_scores(text)
                
                print("\nAnálisis de Sentimiento:")
                print(f"Negativo: {sentiment_score['neg']}")
                print(f"Neutral: {sentiment_score['neu']}")
                print(f"Positivo: {sentiment_score['pos']}")
                print(f"Compuesto: {sentiment_score['compound']}")  # Compuesto mide el sentimiento general
            else:
                print("No se encontró el cuerpo de la noticia.")
        else:
            print("No se encontró el cuerpo del HTML.")

# Ruta del archivo HTML descargado (ajusta la ruta según tu ubicación del archivo)
file_path = 'press_releases/TSLA_press_2024-07-23.html'

# Extrae y analiza el texto del HTML
extract_text_from_html(file_path)
