import threading
import time
import random
import json
import requests
from base64 import b64encode, b64decode
from os import urandom
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from ascon import ascon_encrypt, ascon_decrypt

SERVER_URL = "http://localhost:5000/"
SEND_INTERVAL = 5
SHARED_KEYS = {
    "aes": b"claveaesclaveaes",        # 16 bytes (AES-128)
    "chacha": b"clavesecretachacha20clave1234567",  # 32 bytes (ChaCha20)
    "ascon": b"asconclave123456"  # 16 bytes
}

def generate_sensor_data(device_id):
    return {
        "device_id": f"esp32_{device_id}",
        "temperature": round(random.uniform(20, 30), 2),
        "humidity": round(random.uniform(40, 80), 2),
        "pressure": round(random.uniform(980, 1020), 2),
        "altitude": round(random.uniform(10, 50), 2),
        "light": random.randint(100, 800),
        "door_angle": 0 if device_id != 0 else 90
    }

KEY_ESP32_TTP = b"esp32sharedkey!!"
SESSION_KEY = None

def ascon_encrypt_message(msg: bytes, key: bytes):
    nonce = urandom(16)
    ct = ascon_encrypt(key, nonce, b"", msg)
    return b64encode(ct).decode(), b64encode(nonce).decode()

def ascon_decrypt_message(ct_b64: str, nonce_b64: str, key: bytes):
    ct = b64decode(ct_b64)
    nonce = b64decode(nonce_b64)
    return ascon_decrypt(key, nonce, b"", ct)

def encrypt_data(data: dict, algorithm: str):
    json_data = json.dumps(data).encode()
    backend = default_backend()

    start = time.perf_counter()
    if algorithm == "aes":
        key = SHARED_KEYS["aes"]
        iv = urandom(16)
        while len(json_data) % 16 != 0:
            json_data += b"\x00"
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
        encrypted = cipher.encryptor().update(json_data) + cipher.encryptor().finalize()
        payload = b64encode(encrypted).decode()
        iv_encoded = b64encode(iv).decode()

    elif algorithm == "chacha":
        key = SHARED_KEYS["chacha"]
        nonce = urandom(16)
        cipher = Cipher(algorithms.ChaCha20(key, nonce), mode=None, backend=backend)
        encrypted = cipher.encryptor().update(json_data)
        payload = b64encode(encrypted).decode()
        iv_encoded = b64encode(nonce).decode()

    elif algorithm == "ascon":
        key = SESSION_KEY  # Clave de sesión generada por el TTP
        if key is None:
            raise ValueError("SESSION_KEY no ha sido establecido aún")
        nonce = urandom(16)
        ct = ascon_encrypt(key, nonce, b"", json_data)
        payload = b64encode(ct).decode()
        iv_encoded = b64encode(nonce).decode()

    else:
        raise ValueError("Algoritmo desconocido")

    elapsed = (time.perf_counter() - start) * 1000   # tiempo en ms
    return {
        "payload": payload,
        "iv": iv_encoded,
        "algorithm": algorithm,
        "time_ms": round(elapsed, 3)
    }

def authenticate():
    nonce = f"nonce-{int(time.time())}".encode()
    enc_nonce, iv = ascon_encrypt_message(nonce, SESSION_KEY)
    resp = requests.post(f"{SERVER_URL}/server_auth", json={"nonce": enc_nonce, "iv": iv})
    decrypted = ascon_decrypt_message(resp.json()['response'], resp.json()['iv'], SESSION_KEY).decode()
    if decrypted == nonce.decode() + "OK":
        print("Autenticación mutua completada con éxito")
    else:
        print("Autenticación fallida")

def simulator(device_id, algorithm):
    while True:
        sensor_data = generate_sensor_data(device_id)
        try:
            enc_data = encrypt_data(sensor_data, algorithm)
            time_ms = enc_data.pop("time_ms")
            response = requests.post(f"{SERVER_URL}/rt_measurements", json=enc_data)
            print(f"[ESP32-{device_id}] Algoritmo: {algorithm.upper()} | Estado: {response.status_code} | Tiempo cifrado: {time_ms} ms")
        except Exception as e:
            print(f"[ESP32-{device_id}] Error: {e}")
        time.sleep(SEND_INTERVAL)


def iniciar_sesion_y_autenticar():
    global SESSION_KEY
    print("[ESP32] Solicitando clave al TTP...")
    r = requests.post(f"{SERVER_URL}/ttp_generate_key").json()
    key = r['to_esp32']['key']
    iv = r['to_esp32']['iv']
    SESSION_KEY = ascon_decrypt_message(key, iv, KEY_ESP32_TTP)
    print("[ESP32] Clave de sesión establecida")

    requests.post(f"{SERVER_URL}/server_receive_key", json=r['to_server'])
    authenticate()


if __name__ == '__main__':
    iniciar_sesion_y_autenticar()
    ALGORITHMS = ["aes", "chacha", "ascon"] 
    for i, algo in enumerate(ALGORITHMS):   
        threading.Thread(target=simulator, args=(i, algo), daemon=True).start()     
    while True:
        time.sleep(1)

