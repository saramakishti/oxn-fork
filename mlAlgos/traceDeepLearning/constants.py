SERVICE_NAME_COLUMN = "service_name"
SPAN_ID_COLUMN = "span_id"
REF_TYPE_SPAN_ID = "ref_type_span_ID"
DURATION_COLUMN = "duration"
TRACE_ID_COLUMN = "trace_id"

NOT_AVAILABLE = "N/A"

'''
To build the adjency matrix and construct input vectors for the MLP classifier we need need a constant mapping so each vector has the same structure.
This list comes from the opentelemetry-demo source code wihtin this repository and should be updated if the demo changes or another version is taken.

The Integers as corresponding values will be the corresponding index values to build the Adj. Matrix

'''
SERVICES = {
     "N/A": 0,
     "frontend-proxy": 1,
     "frontend": 2,
     "featureflagservice": 3,
     "accountingservice": 4,
     "adservice": 5,
     "checkoutservice": 6,
     "currencyservice": 7,
     "emailservice": 8,
     "frauddetectionservice": 9,
     "paymentservice": 10,
     "productcatalogservice": 11,
     "quoteservice": 12,
     "recommendationservice": 13,
     "shippingservice": 14,
     "cartservice": 15
}


SERVICES = {
    "N/A": 0,
    "frontend-proxy": 1,
    "frontend": 2,
    "featureflagservice": 3,
    "accountingservice": 4,
    "adservice": 5,
    "checkoutservice": 6,
    "currencyservice": 7,
    "emailservice": 8,
    "frauddetectionservice": 9,
    "paymentservice": 10,
    "productcatalogservice": 11,
    "quoteservice": 12,
    "recommendationservice": 13,
    "shippingservice": 14,
    "cartservice": 15
}


SERVICES_REVERSE = {
    0: "N/A",
    1: "frontend-proxy",
    2: "frontend",
    3: "featureflagservice",
    4: "accountingservice",
    5: "adservice",
    6: "checkoutservice",
    7: "currencyservice",
    8: "emailservice",
    9: "frauddetectionservice",
    10: "paymentservice",
    11: "productcatalogservice",
    12: "quoteservice",
    13: "recommendationservice",
    14: "shippingservice",
    15: "cartservice"
}


