'''
This file emulates the otel-collector Microservice in the Opentelemtry-demo which acts as a producer for the Kafka Queue
'''
from kafka import KafkaProducer
import json
import time

with open('./data/paymentService.json', 'r') as file:
    data = json.load(file)


KAFKA_SERVER = 'localhost:9092'
TOPIC_NAME = 'trace-data'

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_SERVER],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_message(value):
    producer.send(TOPIC_NAME, value=value)
    producer.flush()
    print(f"Sent: {value}")

 
for trace in data[data]:
    send_message(trace)
    time.sleep(1)


producer.close()
