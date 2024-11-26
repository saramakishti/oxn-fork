SERVICE_NAME_COLUMN = "service_name"
SPAN_ID_COLUMN = "span_id"
REF_TYPE_SPAN_ID = "ref_type_span_ID"
DURATION_COLUMN = "duration"
TRACE_ID_COLUMN = "trace_id"

'''
To build the adjency matrix and construct input vectors for the MLP classifier we need need a constant mapping so each vector has the same structure.
This list comes from the opentelemetry-demo source code wihtin this repository and should be updated if the demo changes or another version is taken.

The Integers as corresponding values will be the corresponding index values to build the Adj. Matrix

'''
SERVICES = {
     "N/A": 0,
     "frontend-proxy" : 0,
     "featureflagservice" :1,
     "frontend" : 2,
     "accountingservice" : 3,
     "adservice" : 4,
     "checkoutservice": 5,
     "currencyservie": 6,
     "emailservice": 7,
     # ffpostgres is not instrumented
     "frauddetectionservice" : 8,
     "paymentservice" : 9,
     "productcatalogservice": 10,
     "quoteservice": 11,
     "recommendationservice": 12,
     "shippingservice": 13,
     "cartservice": 14
}

