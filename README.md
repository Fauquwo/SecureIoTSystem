# 🔐 Secure IoT System

Este proyecto implementa un sistema seguro de comunicación entre nodos IoT y un servidor central, utilizando cifrado simétrico, autenticación mutua y un tercero de confianza (TTP).

## 📦 Estructura

- `SimlacionESP32.py`: Simula múltiples nodos ESP32 que cifran y envían datos al servidor.
- `ServidorFlask.py`: Servidor que recibe, descifra, autentica y muestra los datos.
- `datos.csv`: Archivo generado automáticamente con datos recibidos.
- `README.md`: Documentación del proyecto.

## 🔐 Algoritmos de cifrado soportados

- **AES-CBC** (bloque, 128 bits)
- **ChaCha20** (flujo, 256 bits)
- **ASCON** (AEAD, usado para TTP y datos cifrados con `session_key`)

## 🔁 Protocolo TTP

1. ESP32 solicita clave al TTP (`/ttp_generate_key`)
2. TTP genera una `session_key` y la cifra para ESP32 y el servidor usando ASCON
3. El servidor y ESP32 comparten la misma clave temporal

## 🔑 Autenticación mutua

- El nodo ESP32 genera un `nonce`, lo cifra y lo envía al servidor
- El servidor responde con `nonce+OK`, cifrado con la misma clave
- Si el nodo valida la respuesta, la autenticación es exitosa

## 📊 Análisis de rendimiento

Cada nodo registra el tiempo de cifrado (`Tiempo cifrado`) para comparar la eficiencia entre los algoritmos.

## 🌐 Visualización Web

- Visita `http://localhost:5000` para ver los datos recibidos
- Actualización automática cada 3 segundos
