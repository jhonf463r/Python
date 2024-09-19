import tensorflow as tf
from tensorflow import keras
import numpy as np

# Ejemplo de datos de entrenamiento
conversations = [
    ("Hola, ¿cómo estás?", "¡Hola! Estoy bien, gracias por preguntar. ¿En qué puedo ayudarte hoy en nuestra tienda virtual?"),
    ("¿Qué haces?", "¡Hola! Estoy aquí para asistirte con cualquier pregunta que tengas sobre nuestros productos. ¿Hay algo específico que buscas?"),
    ("¿Tienen promociones?", "¡Claro que sí! Tenemos varias promociones activas en este momento. Te invito a visitar nuestra sección de ofertas especiales en nuestra página web."),
    ("¿Cuánto cuesta el producto X?", "El producto X tiene un precio de $XX. Además, si compras hoy, puedes aprovechar un descuento del 10%. ¿Te gustaría más información?"),
    ("¿Hacen envíos a todo el país?", "¡Sí! Hacemos envíos a todo el país. Además, si tu compra supera los $YY, el envío es gratuito."),
    ("¿Qué métodos de pago aceptan?", "Aceptamos varias formas de pago, incluyendo tarjetas de crédito, débito y pagos en efectivo a través de OXXO. ¿Hay algún otro detalle que necesites saber?"),
    ("¿Cuánto tarda en llegar mi pedido?", "El tiempo de entrega varía según tu ubicación, pero generalmente toma entre 3 y 5 días hábiles. Además, ofrecemos opciones de envío rápido. ¿Te gustaría saber más?"),
    ("¿Puedo devolver un producto si no me gusta?", "¡Por supuesto! Tenemos una política de devolución de 30 días. Si no estás satisfecho con tu compra, puedes devolver el producto en su estado original para un reembolso completo."),
    ("¿Dónde están ubicados?", "Nuestra tienda es virtual, pero puedes contactarnos en cualquier momento a través de nuestra página web o redes sociales. ¿Cómo puedo asistirte hoy?"),
    ("¿Tienen tienda física?", "Actualmente operamos únicamente de manera virtual, lo que nos permite ofrecerte los mejores precios. ¿Hay algo en particular que estás buscando?"),
    ("¿Tienen garantía en sus productos?", "Sí, todos nuestros productos vienen con una garantía de 1 año. ¿Te gustaría más información sobre algún producto en particular?"),
    ("¿Cómo puedo contactar con atención al cliente?", "Puedes contactarnos a través de nuestro chat en vivo en la página web, o enviarnos un correo a servicio@tienda.com. Estamos aquí para ayudarte."),
    ("¿Tienen productos nuevos?", "¡Sí! Constantemente actualizamos nuestro catálogo con los últimos productos. Te invito a visitar la sección de 'Novedades' en nuestra página web."),
    ("¿Qué productos recomiendas?", "Depende de lo que estés buscando. Tenemos una sección de 'Productos más vendidos' y 'Recomendados' en nuestra página web que podría interesarte. ¿Hay algo específico que te gustaría encontrar?"),
    ("¿Puedo rastrear mi pedido?", "Sí, una vez que tu pedido sea enviado, recibirás un correo con un número de seguimiento para que puedas rastrear tu paquete en tiempo real."),
    ("¿Tienen descuentos para primeras compras?", "¡Claro! Si es tu primera compra, puedes utilizar el código 'BIENVENIDO10' para obtener un 10% de descuento. ¿Hay algo más en lo que pueda ayudarte?"),
    ("¿Qué diferencia hay entre los modelos X y Y?", "La principal diferencia entre los modelos X y Y es [descripción detallada]. ¿Te gustaría saber más sobre alguno de estos modelos en particular?"),
    ("¿Cómo puedo hacer una compra?", "Hacer una compra es muy sencillo. Solo añade los productos que te gustan al carrito y sigue los pasos para finalizar la compra. Si tienes alguna duda, estamos aquí para ayudarte."),
    ("¿Tienen servicio de atención al cliente?", "¡Sí! Nuestro equipo de atención al cliente está disponible para ayudarte con cualquier pregunta o problema que puedas tener. Puedes contactarnos a través de nuestro chat en vivo o correo electrónico."),
    ("¿Puedo cambiar la dirección de entrega?", "Sí, puedes cambiar la dirección de entrega antes de que el pedido sea enviado. Por favor, contáctanos lo antes posible para realizar el cambio."),
    ("¿Puedo cancelar mi pedido?", "Sí, puedes cancelar tu pedido antes de que sea enviado. Contáctanos rápidamente y te ayudaremos con el proceso de cancelación."),
    ("¿Ofrecen envío internacional?", "Actualmente solo realizamos envíos dentro del país. Esperamos poder ofrecer envíos internacionales en el futuro. ¿Hay algo más en lo que pueda asistirte?"),
    ("¿Cómo puedo aplicar un cupón de descuento?", "Puedes aplicar tu cupón de descuento en la sección de 'Carrito de compras' antes de finalizar tu pedido. ¿Necesitas ayuda con algo más?"),
    ("¿Puedo pagar a plazos?", "Sí, ofrecemos opciones de pago a plazos con tarjetas de crédito seleccionadas. ¿Te gustaría más información sobre esta opción?"),
    ("¿Tienen programa de lealtad?", "¡Sí! Nuestro programa de lealtad te permite ganar puntos con cada compra que luego puedes canjear por descuentos. ¿Te gustaría saber más?"),
    ("¿Puedo recoger mi pedido en algún lugar?", "Actualmente no ofrecemos recogida en tienda, pero hacemos envíos rápidos y seguros a tu domicilio. ¿Hay algo más en lo que pueda asistirte?"),
    ("¿Ofrecen regalos por compra?", "Sí, tenemos promociones especiales donde puedes recibir regalos por tus compras. Visita nuestra página de promociones para más detalles."),
    ("¿Tienen productos ecológicos?", "¡Sí! Contamos con una línea de productos ecológicos y sostenibles. Te invito a explorar nuestra sección de 'Productos Ecológicos' en la página web."),
    ("¿Cómo puedo suscribirme a su boletín?", "Puedes suscribirte a nuestro boletín ingresando tu correo en el campo de suscripción al pie de nuestra página web. Así recibirás las últimas noticias y ofertas."),
    ("¿Dónde puedo ver las opiniones de otros clientes?", "Puedes ver las opiniones de otros clientes en la página de cada producto, en la sección de 'Reseñas'. ¿Te gustaría más información sobre algún producto?"),
    ("¿Puedo solicitar un producto que no está en el catálogo?", "Sí, si estás buscando un producto específico que no ves en nuestro catálogo, contáctanos y haremos lo posible por conseguirlo para ti."),
    ("¿Tienen descuentos para estudiantes?", "Sí, ofrecemos descuentos especiales para estudiantes. Contáctanos para más detalles sobre cómo obtener tu descuento."),
    ("¿Ofrecen envoltura para regalo?", "¡Sí! Ofrecemos envoltura para regalo por un pequeño costo adicional. Puedes seleccionar esta opción al finalizar tu compra."),
    ("¿Puedo cambiar un producto si no me queda bien?", "Sí, puedes cambiar el producto dentro de los 30 días siguientes a la compra. Contáctanos para más información sobre el proceso de cambio."),
    ("¿Cómo puedo hacer un seguimiento de mi pedido?", "Una vez que tu pedido sea enviado, recibirás un correo con el número de seguimiento. Puedes usar este número para rastrear tu pedido en tiempo real."),
    ("¿Ofrecen servicio técnico?", "Sí, contamos con un servicio técnico especializado para asistirte con cualquier problema que puedas tener con nuestros productos. ¿Necesitas ayuda con algo más?"),
    ("¿Qué garantía tienen sus productos?", "Todos nuestros productos vienen con una garantía de 1 año. Si tienes algún problema, no dudes en contactarnos."),
    ("¿Puedo hacer una compra sin registrarme?", "Sí, puedes hacer una compra como invitado, aunque te recomendamos registrarte para aprovechar todos los beneficios y promociones."),
]

# Convertir los datos en un formato adecuado
input_texts, target_texts = zip(*conversations)

# Tokenizar el texto
tokenizer = keras.preprocessing.text.Tokenizer()
tokenizer.fit_on_texts(input_texts + target_texts)
input_sequences = tokenizer.texts_to_sequences(input_texts)
target_sequences = tokenizer.texts_to_sequences(target_texts)

# Padding
input_data = keras.preprocessing.sequence.pad_sequences(input_sequences, padding='post')
target_data = keras.preprocessing.sequence.pad_sequences(target_sequences, padding='post')

# Crear el modelo
model = keras.Sequential([
    keras.layers.Embedding(input_dim=len(tokenizer.word_index) + 1, output_dim=64, input_length=input_data.shape[1]),
    keras.layers.LSTM(64, return_sequences=True),
    keras.layers.LSTM(64),
    keras.layers.Dense(len(tokenizer.word_index) + 1, activation='softmax')
])

model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

# Entrenar el modelo
model.fit(input_data, target_data, epochs=10)

# Guardar el modelo
model.save("chatbot_model.h5")

# Convertir a TensorFlow Lite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()
with open("chatbot_model.tflite", "wb") as f:
    f.write(tflite_model)

print("¡Modelo entrenado y convertido a TensorFlow Lite exitosamente!")
