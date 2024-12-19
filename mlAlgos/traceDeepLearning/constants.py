SERVICE_NAME_COLUMN = "service_name"
SPAN_ID_COLUMN = "span_id"
REF_TYPE_SPAN_ID = "ref_type_span_ID"
DURATION_COLUMN = "duration"
TRACE_ID_COLUMN = "trace_id"
START_TIME = 'start_time'

NOT_AVAILABLE = "N/A"

SUPERVISED_COLUMN = "packet_loss_treatment"

PROJECT_ID = "advanced-cloud-prototyping"

#### constants to access google cloud storage
RAW_DATASETS = "raw_data"
MINED_DATASETS = "mined_datasets"
EVALUATION_DATASETS = "evaluation_datasets"

ADJENCY_TOTAL_PRE = "adjency_total_csv_"


'''
To build the adjency matrix and construct input vectors for the MLP classifier we need need a constant mapping so each vector has the same structure.
This list comes from the opentelemetry-demo source code wihtin this repository and should be updated if the demo changes or another version is taken.

The Integers as corresponding values will be the corresponding index values to build the Adj. Matrix

'''
SERVICES = {
    "frontend-proxy": 0,
    "frontend": 1,
    "featureflagservice": 2,
    "accountingservice": 3,
    "adservice": 4,
    "checkoutservice": 5,
    "currencyservice": 6,
    "emailservice": 7,
    "frauddetectionservice": 8,
    "paymentservice": 9,
    "productcatalogservice": 10,
    "quoteservice": 11,
    "recommendationservice": 12,
    "shippingservice": 13,
    "cartservice": 14
}

SERVICES_REVERSE = {
    0: "frontend-proxy",
    1: "frontend",
    2: "featureflagservice",
    3: "accountingservice",
    4: "adservice",
    5: "checkoutservice",
    6: "currencyservice",
    7: "emailservice",
    8: "frauddetectionservice",
    9: "paymentservice",
    10: "productcatalogservice",
    11: "quoteservice",
    12: "recommendationservice",
    13: "shippingservice",
    14: "cartservice"
}


