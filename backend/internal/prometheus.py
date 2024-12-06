"""
Purpose: Interacts with the Prometheus API.
Functionality: Provides methods to query metrics and labels from Prometheus.
Connection: Used by responses.py and validation.py to gather metrics and validate configurations.

Wrapper around the Prometheus HTTP API"""
import logging
from math import e
import requests
from requests.adapters import Retry, HTTPAdapter

from backend.internal.kubernetes_orchestrator import KubernetesOrchestrator

from backend.internal.models.orchestrator import Orchestrator

from backend.internal.errors import PrometheusException

logger = logging.getLogger(__name__)


# NOTE: prometheus wire timestamps are in milliseconds since unix epoch utc-aware


class Prometheus:
    def __init__(self, orchestrator: Orchestrator, target: str = "sue"):
        assert orchestrator is not None
        self.orchestrator = orchestrator
        self.session = requests.Session()
        retries = Retry(
            total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]
        )
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        address = None
        if isinstance(orchestrator, KubernetesOrchestrator):
            address = orchestrator.get_prometheus_address(target)
        else:
            address = orchestrator.get_prometheus_address()
        self.base_url = f"http://{address}:9090/api/v1/"
        self.endpoints = {
            "range_query": "query_range",
            "instant_query": "query",
            "targets": "targets",
            "labels": "labels",
            "metrics": "label/__name__/values",
            "label_values": "label/%s/values",
            "metric_metadata": "metadata",
            "target_metadata": "targets/metadata",
            "config": "status/config",
            "flags": "status/flags",
        }

    @staticmethod
    def build_query(metric_name, label_dict=None):
        """Build a query in the Prometheus Query Language format"""
        label_string = ""
        query_template = '%s="%s",'
        if label_dict:
            for k, v in label_dict.items():
                interpolated = query_template % (k, v)
                label_string += interpolated
            qry = metric_name + "{%s}" % label_string
        else:
            qry = metric_name
        return qry

    def target_metadata(
        self, match_target: str = None, metric: str = None, limit: int = None
    ):
        """Return metadata about metric with additional target information"""

        params = {
            "match_target": match_target,
            "metric": metric,
            "limit": limit,
        }
        target_metadata = self.endpoints.get("target_metadata")
        if target_metadata is None:
            raise PrometheusException(
                message="Error while getting endpoint for target_metadata",
                explanation="No target target_metadata endpoint returned",
            )
        url = self.base_url + target_metadata
        try:
            response = self.session.get(url=url, params=params)
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.HTTPError) as requests_exception:
            raise PrometheusException(
                message=f"Error while talking to Prometheus at {url}",
                explanation=f"{requests_exception}",
            )

    def targets(self):
        """Return an overview of the current state of Prometheus target discovery"""
        target = self.endpoints.get("targets")
        if target is None:
            raise PrometheusException(
                message="Error while getting endpoint for targets",
                explanation="No target targets endpoint returned",
            )
        url = self.base_url + target
        try:
            response = self.session.get(url=url)
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.HTTPError) as requests_exception:
            raise PrometheusException(
                message=f"Error while talking to Prometheus at {url}",
                explanation=f"{requests_exception}",
            )

    def labels(self, start=None, end=None, match=None):
        """Return label names"""
        params = {
            "start": start,
            "end": end,
            "match": match,
        }
        labels = self.endpoints.get("labels")
        if labels is None:
            raise PrometheusException(
                message="Error while getting endpoint for labels",
                explanation="No target labels endpoint returned",
            )
        url = self.base_url + labels
        try:
            response = self.session.get(
                url, params=params
            )
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.HTTPError) as requests_exception:
            raise PrometheusException(
                message=f"Error while talking to Prometheus at {url}",
                explanation=f"{requests_exception}",
            )

    def metrics(self):
        metrics = self.endpoints.get("metrics")
        if metrics is None:
            raise PrometheusException(
                message="Error while getting endpoint for metrics",
                explanation="No target metrics endpoint returned",
            )
        url = self.base_url + metrics
        try:
            response = self.session.get(url=url)
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.HTTPError) as requests_exception:
            raise PrometheusException(
                message=f"Error while talking to Prometheus at {url}",
                explanation=f"{requests_exception}",
            )

    def label_values(self, label=None, start=None, end=None, match=None):
        label_values = self.endpoints.get("label_values")
        if label_values is None:
            raise PrometheusException(
                message="Error while getting endpoint for label_values",
                explanation="No target label_values endpoint returned",
            )
        endpoint = label_values % label
        url = self.base_url + endpoint

        params = {
            "start": start,
            "end": end,
            "match": match,
        }
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.HTTPError) as requests_exception:
            raise PrometheusException(
                message=f"Error while talking to Prometheus at {url}",
                explanation=f"{requests_exception}",
            )

    def metric_metadata(self, metric=None, limit=None):
        metric_metadata = self.endpoints.get("metric_metadata")
        if metric_metadata is None:
            raise PrometheusException(
                message="Error while getting endpoint for metric_metadata",
                explanation="No target metric_metadata endpoint returned",
            )
        url = self.base_url + metric_metadata
        params = {
            "metric": metric,
            "limit": limit,
        }
        try:
            response = self.session.get(url=url, params=params)
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.HTTPError) as requests_exception:
            raise PrometheusException(
                message=f"Error while talking to Prometheus at {url}",
                explanation=f"{requests_exception}",
            )

    def config(self):
        config = self.endpoints.get("config")
        if config is None:
            raise PrometheusException(
                message="Error while getting endpoint for config",
                explanation="No target config endpoint returned",
            )
        url = self.base_url + config
        try:
            response = self.session.get(url=url)
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.HTTPError) as requests_exception:
            raise PrometheusException(
                message=f"Error while talking to Prometheus at {url}",
                explanation=f"{requests_exception}",
            )

    def flags(self):
        flags = self.endpoints.get("flags")
        if flags is None:
            raise PrometheusException(
                message="Error while getting endpoint for flags",
                explanation="No target flags endpoint returned",
            )
        url = self.base_url + flags
        try:
            response = self.session.get(url=url)
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.HTTPError) as requests_exception:
            raise PrometheusException(
                message=f"Error while talking to Prometheus at {url}",
                explanation=f"{requests_exception}",
            )

    def instant_query(self, query, time=None, timeout=None):
        """Evaluate a Prometheus query instantly"""
        instant_query = self.endpoints.get("instant_query")
        if instant_query is None:
            raise PrometheusException(
                message="Error while getting endpoint for instant_query",
                explanation="No target instant_query endpoint returned",
            )
        url = self.base_url + instant_query
        params = {
            "query": query,
            "time": time,
            "timeout": timeout,
        }
        try:
            response = self.session.get(url=url, params=params)
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.HTTPError) as requests_exception:
            raise PrometheusException(
                message=f"Error while talking to Prometheus at {url}",
                explanation=f"{requests_exception}",
            )

    def range_query(self, query, start, end, step=None, timeout=None):
        """Evaluate a Prometheus query over a time range"""
        range_query = self.endpoints.get("range_query")
        if range_query is None:
            raise PrometheusException(
                message="Error while getting endpoint for range_query",
                explanation="No target range_query endpoint returned",
            )
        url = self.base_url + range_query
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step,
            "timeout": timeout,
        }
        try:
            response = self.session.get(url=url, params=params)
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.HTTPError) as requests_exception:
            raise PrometheusException(
                message=f"Error while talking to Prometheus at {url}",
                explanation=f"{requests_exception}",
            )
