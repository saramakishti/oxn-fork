import json
from locust import HttpUser, TaskSet, task, between

class UserBehavior(TaskSet):
    
    @task(1)
    def index(self):
        self.client.get("/")
    
    @task(10)
    def get_product(self):
        self.client.get("/api/products/0PUK6V6EV0")
    
    @task(3)
    def load_user_data(self):
        # Datei people.json im Container öffnen und laden
        with open('/usr/src/app/experiments/people.json', 'r') as f:
            people = json.load(f)
            print(people)  # Hier kannst du mit den geladenen Daten weiterarbeiten

class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 2)  # Wartezeit zwischen den Tasks
