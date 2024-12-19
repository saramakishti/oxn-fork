# Machine Learning Algorithms for Distributed Tracing Data

This is just for developing and keeping track of decisions we make throughout the process

# Constructing Experiments for the ML Data based in distributed tracing

     One of the questions that hunt me is how much data do we actually need?
     We inject faults into the recommendationservice for example -> do we need to collect data from all microservices in the SUE?

     I tried collecting dis. Traces from all Microservices these were the responses from Jaeger:

          [2024-11-27 14:17:25,161] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture accountingservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,226] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture adservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,271] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture checkoutservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,299] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture currencyservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,413] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture emailservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,472] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture frauddetectionservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,536] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture paymentservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response

     
     Microservices I got data from:
          - frontend
          - frontend-proxy
          - recommendationservice
          - cartservice
     
     For right now these are the the microservices that are also provoked from Locust.... andd the tasks defined in the experiment.

     ==> we need to define very good experiments for the distributed tracing Algorithm and especially locust tasks.

# Data Mining Method 1: Adjency Matrix

     Some service call themselves "recursively" like cartservice. This is a single trace sorted ascending after invacation time.

               service_name span_kind  ref_type_span_ID  duration
     378  frontend-proxy    server               NaN  355311.0
     377  frontend-proxy    client  536d357fb4be5346  355082.0
     381        frontend    server  3c7d0ba472fe68f1  206676.0
     379        frontend    client  24f53e0ccf93136d  120930.0
     382     cartservice    server  0efa07cb43785b04   23861.0
     385     cartservice    client  1d497080248a57dd    9120.0
     386     cartservice    client  1d497080248a57dd    2198.0
     387     cartservice    client  1d497080248a57dd    1863.0
     380        frontend    client  24f53e0ccf93136d   84384.0
     383     cartservice    server  4b332aa05d7156da    3488.0
     384     cartservice    client  0fb390245f1df848    1623.0

     This can happen because cart_service has redis_cache in the "backend", looking into the source code helps lol.


     Load generation starts outside the frontend proxy for the open-telemetry demo



     




          


