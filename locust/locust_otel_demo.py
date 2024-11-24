#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


import json
import os
import random
import uuid
import logging

from locust import HttpUser, task, between


categories = [
    "binoculars",
    "telescopes",
    "accessories",
    "assembly",
    "travel",
    "books",
    None,
]

products = [
    "0PUK6V6EV0",
    "1YMWWN1N4O",
    "2ZYFJ3GM2N",
    "66VCHSJNUP",
    "6E92ZMYYFZ",
    "9SIQT8TOJO",
    "L9ECAV7KIM",
    "LS4PSXUNUM",
    "OLJCESPC7Z",
    "HQTGWGPNH4",
]

people = """[
    {
        "email": "larry_sergei@example.com",
        "address": {
            "streetAddress": "1600 Amphitheatre Parkway",
            "zipCode": "94043",
            "city": "Mountain View",
            "state": "CA",
            "country": "United States"
        },
        "userCurrency": "USD",
        "creditCard": {
            "creditCardNumber": "4432-8015-6152-0454",
            "creditCardExpirationMonth": 1,
            "creditCardExpirationYear": 2039,
            "creditCardCvv": 672
        }
    },
    {
        "email": "bill@example.com",
        "address": {
            "streetAddress": "One Microsoft Way",
            "zipCode": "98052",
            "city": "Redmond",
            "state": "WA",
            "country": "United States"
        },
        "userCurrency": "USD",
        "creditCard": {
            "creditCardNumber": "4532-4211-7434-1278",
            "creditCardExpirationMonth": 2,
            "creditCardExpirationYear": 2039,
            "creditCardCvv": 114
        }
    },
    {
        "email": "steve@example.com",
        "address": {
            "streetAddress": "One Apple Park Way",
            "zipCode": "95014",
            "city": "Cupertino",
            "state": "CA",
            "country": "United States"
        },
        "userCurrency": "USD",
        "creditCard": {
            "creditCardNumber": "4532-6178-2799-1951",
            "creditCardExpirationMonth": 3,
            "creditCardExpirationYear": 2039,
            "creditCardCvv": 239
        }
    },
    {
        "email": "mark@example.com",
        "address": {
            "streetAddress": "1 Hacker Way",
            "zipCode": "94025",
            "city": "Menlo Park",
            "state": "CA",
            "country": "United States"
        },
        "userCurrency": "USD",
        "creditCard": {
            "creditCardNumber": "4539-1103-5661-7083",
            "creditCardExpirationMonth": 4,
            "creditCardExpirationYear": 2039,
            "creditCardCvv": 784
        }
    },
    {
        "email": "jeff@example.com",
        "address": {
            "streetAddress": "410 Terry Ave N",
            "zipCode": "98109",
            "city": "Seattle",
            "state": "WA",
            "country": "United States"
        },
        "userCurrency": "USD",
        "creditCard": {
            "creditCardNumber": "4916-0816-6217-7968",
            "creditCardExpirationMonth": 5,
            "creditCardExpirationYear": 2039,
            "creditCardCvv": 397
        }
    },
    {
        "email": "reed@example.com",
        "address": {
            "streetAddress": "100 Winchester Circle",
            "zipCode": "95032",
            "city": "Los Gatos",
            "state": "CA",
            "country": "United States"
        },
        "userCurrency": "USD",
        "creditCard": {
            "creditCardNumber": "4929-5431-0337-5647",
            "creditCardExpirationMonth": 6,
            "creditCardExpirationYear": 2039,
            "creditCardCvv": 793
        }
    },
    {
        "email": "tobias@example.com",
        "address": {
            "streetAddress": "150 Elgin St",
            "zipCode": "K2P1L4",
            "city": "Ottawa",
            "state": "ON",
            "country": "Canada"
        },
        "userCurrency": "CAD",
        "creditCard": {
            "creditCardNumber": "4763-1844-9699-8031",
            "creditCardExpirationMonth": 7,
            "creditCardExpirationYear": 2039,
            "creditCardCvv": 488
        }
    },
    {
        "email": "jack@example.com",
        "address": {
            "streetAddress": "1355 Market St",
            "zipCode": "94103",
            "city": "San Francisco",
            "state": "CA",
            "country": "United States"
        },
        "userCurrency": "USD",
        "creditCard": {
            "creditCardNumber": "4929-6495-8333-3657",
            "creditCardExpirationMonth": 8,
            "creditCardExpirationYear": 2039,
            "creditCardCvv": 159
        }
    },
    {
        "email": "moore@example.com",
        "address": {
            "streetAddress": "2200 Mission College Blvd",
            "zipCode": "95054",
            "city": "Santa Clara",
            "state": "CA",
            "country": "United States"
        },
        "userCurrency": "USD",
        "creditCard": {
            "creditCardNumber": "4485-4803-8707-3547",
            "creditCardExpirationMonth": 9,
            "creditCardExpirationYear": 2039,
            "creditCardCvv": 682
        }
    }
]"""

# TODO make this configurable probably?
#people_file = open('opt/oxn/locust/people.json')
people = json.loads(people)

class WebsiteUser(HttpUser):
    wait_time = between(1, 10)

    @task(1)
    def index(self):
        self.client.get("/")

    @task(10)
    def browse_product(self):
        self.client.get("/api/products/" + random.choice(products))

    @task(3)
    def get_recommendations(self):
        params = {
            "productIds": [random.choice(products)],
        }
        self.client.get("/api/recommendations", params=params)

    @task(3)
    def get_ads(self):
        params = {
            "contextKeys": [random.choice(categories)],
        }
        self.client.get("/api/data/", params=params)

    @task(3)
    def view_cart(self):
        self.client.get("/api/cart")

    @task(2)
    def add_to_cart(self, user=""):
        if user == "":
            user = str(uuid.uuid1())
        product = random.choice(products)
        self.client.get("/api/products/" + product)
        cart_item = {
            "item": {
                "productId": product,
                "quantity": random.choice([1, 2, 3, 4, 5, 10]),
            },
            "userId": user,
        }
        self.client.post("/api/cart", json=cart_item)

    @task(1)
    def checkout(self):
        # checkout call with an item added to cart
        user = str(uuid.uuid1())
        self.add_to_cart(user=user)
        checkout_person = random.choice(people)
        checkout_person["userId"] = user
        self.client.post("/api/checkout", json=checkout_person)

    @task(1)
    def checkout_multi(self):
        # checkout call which adds 2-4 different items to cart before checkout
        user = str(uuid.uuid1())
        for i in range(random.choice([2, 3, 4])):
            self.add_to_cart(user=user)
        checkout_person = random.choice(people)
        checkout_person["userId"] = user
        self.client.post("/api/checkout", json=checkout_person)


    def on_start(self):
        self.index()


