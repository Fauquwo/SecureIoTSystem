import pandas as pd
import requests
from datetime import datetime
import os

# 配置 InfluxDB 信息
INFLUX_URL = "http://127.0.0.1:8086"
INFLUX_TOKEN = "tFTMD-vI0YJlxMYxPVTS6SvBMISbB2SQv4e9GLTE66PmbEU8DdynByLNHR1CmWGwLvuX1uF4aB4ClCRg3a4SvQ=="
ORG = "SistemasinformaticosIoT"
BUCKET_NAME = "bucket3"
QUERY_URI = f"{INFLUX_URL}/api/v2/write?org={ORG}&bucket={BUCKET_NAME}&precision=ms"
HEADERS = {'Authorization': f'Token {INFLUX_TOKEN}'}

# 加载 CSV 文件
CSV_DIR = "csv_data"
CSV_FILE_PATH = os.path.join(CSV_DIR, "sensor_data.csv")
data = pd.read_csv(CSV_FILE_PATH)

# 上传数据到 InfluxDB
def upload_to_influxdb(row):
    try:
        # 转换 timestamp 为 Unix 毫秒时间戳
        timestamp = int(datetime.strptime(row["timestamp"], "%Y/%m/%d %H:%M").timestamp() * 1000)

        # 构建 InfluxDB 行协议格式
        line_protocol = (
            f"sensor_data "
            f"temperature={row['temperature']},"
            f"humidity={row['humidity']},"
            f"pressure={row['pressure']},"
            f"altitude={row['altitude']},"
            f"light={row['light']},"
            f"door_angle={row['door_angle']} "
            f"{timestamp}"
        )

        # 发送数据到 InfluxDB
        response = requests.post(QUERY_URI, data=line_protocol, headers=HEADERS)
        if response.status_code == 204:
            print(f"数据上传成功: {line_protocol}")
        else:
            print(f"数据上传失败: {response.status_code}, {response.text}")

    except Exception as e:
        print(f"处理行时出错: {e}")

# 遍历每一行并上传
for _, row in data.iterrows():
    upload_to_influxdb(row)
