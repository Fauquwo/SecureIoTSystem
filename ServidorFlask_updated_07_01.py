import os
import time
import pandas as pd
import requests
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Usado para la gestión de sesiones

# Configuración
INFLUX_URL = "127.0.0.1"
INFLUX_TOKEN = "5phA3e3E8SU6k02r7wzj3_HcmIMQmuyVclu1X-aYnGwoUfayYXYjqbeYEJNMVnETvWK1p-j0FDqppFuzohA37Q=="
ORG = "SistemasinformaticosIoT"
BUCKET_NAME = "bucket3"
QUERY_URI = 'http://{}:8086/api/v2/write?org={}&bucket={}&precision=ms'.format(INFLUX_URL,ORG,BUCKET_NAME)
HEADERS = {'Authorization': f'Token {INFLUX_TOKEN}'}

# Directorio para almacenar los archivos CSV
CSV_DIR = "csv_data"
os.makedirs(CSV_DIR, exist_ok=True)
CSV_FILE_PATH = os.path.join(CSV_DIR, "sensor_data.csv")

# Estado inicial
motor_state = {'angle': 0, 'pending_change': False}  # Posición inicial de la puerta: abierta (0°)
thresholds = {
    'max_temp': {'value': 30.0, 'description': 'máximo de temperatura', 'state':'updated'},
    'min_temp': {'value': 20.0, 'description': 'mínimo de temperatura', 'state':'updated'},
    'max_humidity': {'value': 80.0, 'description': 'máximo de humedad', 'state':'updated'},
    'min_humidity': {'value': 20.0, 'description': 'mínimo de humedad', 'state':'updated'}
}
sensor_data = {'temperature': None, 'humidity': None, 'pressure': None, 'altitude': None, 'light': None, 'door_angle': None}  # Datos actuales de sensores

# Credenciales de inicio de sesión
USERNAME = "admin" #poner placa asociada a user
PASSWORD = "admin123"
USERS = {
    'admin': {'password': 'admin123', 'role': 'admin'},
    'user1': {'password': 'user111', 'role': 'user'}
}

# Función para agregar datos automáticamente
def append_sensor_data(data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_with_timestamp = {
        "timestamp": timestamp,
        "temperature": data.get("temperature", "null"),
        "humidity": data.get("humidity", "null"),
        "pressure": data.get("pressure", "null"),
        "altitude": data.get("altitude", "null"),
        "light": data.get("light", "null"),
        "door_angle": data.get("door_angle", "null")
    }

    # Si el archivo no existe, crea un nuevo archivo con encabezados
    file_exists = os.path.isfile(CSV_FILE_PATH)
    fieldnames = ["timestamp", "temperature", "humidity", "pressure", "altitude", "light", "door_angle"]

    # Usar pandas para manejar la escritura en el archivo CSV
    df = pd.DataFrame([data_with_timestamp])
    if not file_exists:
        df.to_csv(CSV_FILE_PATH, mode="a", index=False, header=True)
    else:
        df.to_csv(CSV_FILE_PATH, mode="a", index=False, header=False)
    
    influx_data = f"sensor_data temperature={data_with_timestamp['temperature']},humidity={data_with_timestamp['humidity']},pressure={data_with_timestamp['pressure']},altitude={data_with_timestamp['altitude']},light={data_with_timestamp['light']},door_angle={data_with_timestamp['door_angle']}"
    response = requests.post(QUERY_URI, data=influx_data, headers=HEADERS)
    if response.status_code != 204:
        print(f"Error al enviar datos a InfluxDB: {response.status_code}, {response.text}")


@app.route('/')
def index():

    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    html_template = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Sistema de Monitoreo IoT</title>
        <style type="text/css">
            /* Estilo general de la página */
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(to bottom, #e3f2fd, #bbdefb);
                min-height: 95vh;
            }

            /* Encabezados */
            h1 {
                text-align: center;
                color: #1565c0;
                margin-top: 20px;
            }

            h2 {
                color: #0d47a1;
                margin-left: 20px;
            }

            /* Contenedor principal */
            .container {
                width: 80%;
                margin: 20px auto;
                background: #ffffff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                min-height: 75vh;

            }
            .tg {
                border-collapse: collapse;
                border-spacing: 0;
                border-width: 3px;
                border-style: solid;
                border-color: black;
            }
            .tg th {
                border-color: black;
                font-family: Arial, sans-serif;
                font-size: 15px;
                padding: 10px 15px;
            }
            .tg .tg-l7yf {
                background-color: #69d9f9;
                font-style: italic;
                font-weight: bold;
                text-align: left;
                vertical-align: top;
            }
            .tg .tg-0qe0 {
                background-color: #ecf4ff;
                text-align: left;
                vertical-align: center;
                padding: 10px 10px;
            }
            /* Botones de acciones */
            .actions button {
                background-color: #1976d2;
                color: #fff;
                border: none;
                padding: 10px 15px;
                margin: 5px;
                border-radius: 5px;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            .actions button:hover {
                background-color: #0d47a1;
            }
            /* Pie de página */
            .footer {
                position: fixed;
                bottom: 0;
                width: 100%;
                background-color: #ecf4ff;
                margin-top: 40px;
                text-align: center;
                font-size: 12px;
                color: #555;
                padding: 2px 0;
                box-shadow: 0 -4px 8px rgba(0, 0, 0, 0.1);
            }
        </style>
    </head>
    <body>
        <h1>Sistema de Monitoreo IoT</h1>
        <div class="container">
            <h2>Datos actuales de los sensores</h2>
            <table class="tg" border="1">
                <tr>
                    <th class="tg-l7yf"><strong>Presión</strong></th>
                    <td class="tg-0qe0">{{ pressure }} hPa</td>
                </tr>
                <tr>
                    <th class="tg-l7yf"><strong>Temperatura</strong></th>
                    <td class="tg-0qe0">{{ temperature }} °C</td>
                </tr>
                <tr>
                    <th class="tg-l7yf"><strong>Altitud</strong></th>
                    <td class="tg-0qe0">{{ altitude }} m</td>
                </tr>
                <tr>
                    <th class="tg-l7yf"><strong>Humedad</strong></th>
                    <td class="tg-0qe0">{{ humidity }} %</td>
                </tr>
                <tr>
                    <th class="tg-l7yf"><strong>Luz</strong></th>
                    <td class="tg-0qe0">{{ light }} lux</td>
                </tr>
            </table>
            <h2>Umbrales actuales</h2>
            <ul>
                {% for key, threshold in thresholds.items() %}
                    <li>Umbral {{ threshold['description'] }}: {{ threshold['value'] }} {% if 'temp' in key %}°C{% elif 'humidity' in key %}%{% endif %}</li>
                {% endfor %}
            </ul>
            <h2>Acciones</h2>
                <div class="actions">
                <button class="admin-only" onclick="modifyThreshold()">Modificar umbrales ambientales</button>
                <button class="admin-only" onclick="controlDoor('open')">Abrir puerta</button>
                <button class="admin-only" onclick="controlDoor('close')">Cerrar puerta</button>
                <button onclick="viewInfluxDB()">Ver datos en InfluxDB</button>
                <p id="response"></p>
                </div>
        </div>
        <script>
            let lastDoorActionTime = null;        

            const userRole = "{{ role }}";  // Flask inyecta el rol aquí

            // Ocultar secciones de admin si el usuario no es admin
            if (userRole !== 'admin') {
                document.querySelectorAll('.admin-only').forEach(element => {
                    element.style.display = 'none';
                });
            } 

            function modifyThreshold() {
                // Crear un menú desplegable para seleccionar el parámetro
                let paramSelect = `<label for="param">Selecciona el parámetro a modificar:</label>
                                <select id="param">
                                    <option value="max_temp">Máximo de Temperatura</option>
                                    <option value="min_temp">Mínimo de Temperatura</option>
                                    <option value="max_humidity">Máximo de Humedad</option>
                                    <option value="min_humidity">Mínimo de Humedad</option>
                                </select>
                                <br><br>
                                <label for="newValue">Introduce el nuevo valor:</label>
                                <input type="number" id="newValue" required>
                                <br><br>
                                <button onclick="submitThreshold()">Actualizar</button>`;

                // Mostrar el menú
                document.getElementById("response").innerHTML = paramSelect;
            }

            function submitThreshold() {
                let param = document.getElementById("param").value;
                let newThreshold = document.getElementById("newValue").value;

                // Verificar que el nuevo valor esté presente
                if (newThreshold) {
                    fetch(`/set_threshold?param=${param}&value=${newThreshold}`, { method: 'POST' })
                    .then(response => {
                        if (response.ok) {
                            return response.json(); // Éxito, parsear JSON
                        } else {
                            // Devolver el cuerpo JSON del error para obtener el mensaje específico
                            return response.json().then(err => {
                                throw new Error(err.message || "Hubo un error al actualizar el umbral.");
                            });
                        }
                    })
                    .then(data => {
                        document.getElementById("response").innerText = data.message;
                        window.location.reload(); // Solo si fue exitoso
                    })
                    .catch(error => {
                        // Mostrar el mensaje de error específico del servidor
                        document.getElementById("response").innerText = error.message;
                    });
                } else {
                    document.getElementById("response").innerText = "Por favor, introduce un valor válido.";
                }
            }

            function controlDoor(action) {
                fetch('/motor', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: action, authorized: true })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById("response").innerText = data.message;
                    if(data.message=='La puerta se ha abierto a 90°'){
                        lastDoorActionTime = new Date();
                    } else{
                        lastDoorActionTime = null;
                    }
                });
            }

            function importCsv() {
                fetch('/import_csv', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById("response").innerText = data.message;
                });
            }

            function viewInfluxDB() {
                const influxDBUrl = `http://${window.location.hostname}:8086`;
                window.open(influxDBUrl, '_blank');
            }
            function checkDoorStatus() {
                if(lastDoorActionTime){
                    const currentTime = new Date();
                    const timeElapsed = Math.floor((currentTime - lastDoorActionTime) / 1000); // Diferencia en segundos
                    if(timeElapsed>=30){
                        fetch('/get_door_state')
                        .then(response => response.json())
                        .then(data => {
                            if (data.door_state) {
                                document.getElementById("response").innerText = "La puerta se ha cerrado automáticamente";
                                lastDoorActionTime = null;
                            }
                        });
                    }
                }              
            }
            setInterval(checkDoorStatus, 1000);
            
        </script>
        <div class="footer">
            <p>2025 Sistema de Monitoreo IoT. Universidad Carlos III de Madrid - Proyecto de demostración de Sistemas Informáticos en IoT.</p>
        </div>
    </body>
    </html>
    """
    
    role = session.get('role', 'user') 
    return render_template_string(html_template, 
                                  temperature=sensor_data['temperature'] or 'No disponible',
                                  humidity=sensor_data['humidity'] or 'No disponible',
                                  pressure=sensor_data['pressure'] or 'No disponible',
                                  altitude=sensor_data['altitude'] or 'No disponible',
                                  light=sensor_data['light'] or 'No disponible',
                                  thresholds=thresholds,
                                  angle=motor_state['angle'],
                                  role=role)

@app.route('/login', methods=['GET', 'POST'])
def login():

    # Página de inicio de sesión del usuario
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = USERS.get(username)
        if user and password == user['password']:
            session['logged_in'] = True
            session['role']=user['role']
            return redirect(url_for('index'))
        else:
            return "Nombre de usuario o contraseña incorrectos. Por favor, inténtalo de nuevo."

    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Inicio de sesión</title>
    </head>
    <body>
        <h1>Inicio de sesión</h1>
        <form method="POST">
            <label for="username">Nombre de usuario:</label>
            <input type="text" id="username" name="username" required>
            <br>
            <label for="password">Contraseña:</label>
            <input type="password" id="password" name="password" required>
            <br>
            <button type="submit">Iniciar sesión</button>
        </form>
    </body>
    </html>
    """

@app.route('/get_door_state')
def get_door_state():
    door_state=False
    if(sensor_data['door_angle']==0 and motor_state['angle']!=sensor_data['door_angle']):
        door_state = True
        motor_state['angle']=0
    return jsonify({'door_state': door_state})

@app.route('/set_threshold', methods=['POST'])
def set_threshold():
    if session.get('role') != 'admin':
        return jsonify({'message': 'Acceso denegado'}), 403

    # Establecer un nuevo umbral de temperatura
    param=request.args.get('param')
    new_value = float(request.args.get('value'))

    if param == 'min_temp' and new_value > thresholds['max_temp']['value']:
        return jsonify({'message': 'El valor mínimo de temperatura no puede superar el máximo.'}), 400
    if param == 'max_temp' and new_value < thresholds['min_temp']['value']:
        return jsonify({'message': 'El valor máximo de temperatura no puede ser inferior al mínimo.'}), 400
    if param == 'min_humidity' and new_value > thresholds['max_humidity']['value']:
        return jsonify({'message': 'El valor mínimo de humedad no puede superar el máximo.'}), 400
    if param == 'max_humidity' and new_value < thresholds['min_humidity']['value']:
        return jsonify({'message': 'El valor máximo de humedad no puede ser inferior al mínimo.'}), 400

    thresholds[param]['value'] = float(new_value)
    thresholds[param]['state'] = 'changed'
    return jsonify({'message': f''}),200

@app.route('/get_threshold', methods=['GET'])
def get_threshold():
    
    # Arduino solicita el valor actual del umbral de temperatura
    return jsonify(thresholds), 200

@app.route('/motor', methods=['GET', 'POST'])
def control_motor():
    if request.method == 'POST':
        if session.get('role') != 'admin':
            return jsonify({'message': 'Acceso denegado'}), 403

        # Control de la puerta mediante el motor
        data = request.get_json()
        action = data.get('action')
        authorized = data.get('authorized', False)

        if not authorized:
            return jsonify({'error': 'Operación no autorizada'}), 403

        if action == 'open' and sensor_data['door_angle'] != 90:
            motor_state['angle'] = 90
            motor_state['pending_change'] = True
            return jsonify({'message': 'La puerta se ha abierto a 90°'})
        elif action == 'close' and sensor_data['door_angle'] != 0:
            motor_state['angle'] = 0
            motor_state['pending_change'] = True
            return jsonify({'message': 'La puerta se ha cerrado a 0°'})
        else:
            return jsonify({'message': 'La puerta ya está en el estado deseado'})
    
    elif request.method == 'GET':
        if motor_state['pending_change'] == True:
            motor_state['pending_change'] = False
            print(motor_state['angle'])
            return str(motor_state['angle']), 200
        else:
            return '', 204

@app.route('/import_csv', methods=['POST'])
def import_csv():

    # Importar datos desde un archivo CSV a InfluxDB
    csv_files = sorted([f for f in os.listdir(CSV_DIR) if f.endswith('.csv')], reverse=True)
    if not csv_files:
        return jsonify({'error': 'No hay archivos CSV disponibles'}), 400

    latest_csv = os.path.join(CSV_DIR, csv_files[0])
    csvReader = pd.read_csv(latest_csv)
    measurement_name = 'sensor_data'

    for _, row in csvReader.iterrows():
        dataE = [f'{measurement_name},temperature={row["temperature"]},humidity={row["humidity"]} ' +
                 f'pressure={row["pressure"]},altitude={row["altitude"]},light={row["light"]}']
        dataEnvio = '\n'.join(dataE)

        # Realizar la solicitud POST
        r = requests.post(QUERY_URI, data=dataEnvio, headers=HEADERS)
        if r.status_code != 204:
            return jsonify({'error': f'Error al enviar datos: {r.status_code}'}), 500

        time.sleep(1)

    return jsonify({'status': 'success', 'message': f'Datos importados desde {latest_csv} a InfluxDB'}), 200

@app.route('/rt_measurements', methods=['POST'])
def rt_measurements():
    #Envío datos en TR desde la placa
    global sensor_data
    new_data = request.get_json()
    sensor_data.update(new_data)
    print("---------------- He recibido --------------------")
    print("Valor de Temperatura mediante POST: " + str(sensor_data['temperature']) + " *C")
    print("Valor de Presion mediante POST: " + str(sensor_data['pressure']) + " hPa")
    print("Valor de Altitud mediante POST: " + str(sensor_data['altitude']) + " m")
    print("Valor de Humedad mediante POST: " + str(sensor_data['humidity']) + " %")
    print("Valor de Luz mediante POST: " + str(sensor_data['light']) + " lux")
    print("-------------------------------------------------")
    

    append_sensor_data(sensor_data)
    return "Datos de sensores recibidos por el servidor correctamente", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
