
from flask import Flask, request, jsonify, render_template_string
from base64 import b64encode
from os import urandom
from ascon import ascon_encrypt

app = Flask(__name__)

KEY_ESP32_TTP = b"esp32sharedkey!!"
KEY_SERVER_TTP = b"serversharedkey!"

def ascon_encrypt_message(msg: bytes, key: bytes):
    nonce = urandom(16)
    ct = ascon_encrypt(key, nonce, b"", msg)
    return b64encode(ct).decode(), b64encode(nonce).decode()

@app.route('/ttp_generate_key', methods=['POST'])
def ttp_generate_key():
    session_key = urandom(16)
    to_esp32_ct, to_esp32_iv = ascon_encrypt_message(session_key, KEY_ESP32_TTP)
    to_server_ct, to_server_iv = ascon_encrypt_message(session_key, KEY_SERVER_TTP)
    return jsonify({
        'to_esp32': {'key': to_esp32_ct, 'iv': to_esp32_iv},
        'to_server': {'key': to_server_ct, 'iv': to_server_iv},
        'session_key': b64encode(session_key).decode()  # Opcional: para debug
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)  # Escucha en el puerto 6000