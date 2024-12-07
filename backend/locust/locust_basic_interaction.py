from locust import HttpUser, TaskSet, task, between

class UserBehavior(TaskSet):

    @task(1)
    def index(self):
        self.client.get("/")

    @task(10)
    def get_product(self):
        self.client.get("/api/products/0PUK6V6EV0")

    @task(3)
    def get_recommendations(self):
        self.client.get("/api/recommendations", params={"productIds": ["1YMWWN1N4O"]})

    @task(3)
    def get_cart(self):
        self.client.get("/api/cart")

    @task(3)
    def get_data(self):
        self.client.get("/api/data", params={"contextKeys": ["accessories"]})

    @task(2)
    def add_to_cart(self):
        self.client.post("/api/cart", json={
            "item": {"productId": "6E92ZMYYFZ", "quantity": 2},
            "userId": 'ab2d0fc0-7224-11ec-8ef2-b658b885fb3',
        })

class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 2)  # Adjust wait_time as necessary
