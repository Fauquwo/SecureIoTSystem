import requests
import json
import time


FLASK_URL = "http://127.0.0.1:5000/rt_measurements"

sensor_data = {
    "temperature": 25.5,
    "humidity": 48.2,
    "pressure": 1012.8,
    "altitude": 305.4,
    "light": 186.3,
    "door_angle": 0
}

for i in range(10):
    sensor_data["temperature"] += 0.5  # Simula un cambio en la temperatura
    sensor_data["humidity"] += 0.4  # Simula un cambio en la humedad
    response = requests.post(FLASK_URL, json=sensor_data)
    print("Estado:", response.status_code)
    print("Contenido:", response.text)
    time.sleep(5)  # Espera 5 segundos entre cada envío

