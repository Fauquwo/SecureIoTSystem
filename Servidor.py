import requests

url = "http://localhost:5000/rt_measurements"
headers = {"Content-Type": "application/json"}
data = {
    "temperature": 31.0,
    "humidity": 47.0,
    "pressure": 1303.0,
    "light": 92,
    "altitude": 1912,
    "door_angle":0

}

response = requests.post(url, json=data, headers=headers)
print("Status Code:", response.status_code)
print("Response Body:", response.json())

