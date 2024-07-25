import unittest
import yaml


from oxn.kubernetes_orchestrator import KubernetesOrchestrator
from oxn.tests.unit.spec_mocks import kubernetes_experiment
from oxn.models.orchestrator import Orchestrator


class KubernetesOrchestrationTest(unittest.TestCase):
    spec = kubernetes_experiment
    loaded_spec = yaml.safe_load(spec)

    def setUp(self) -> None:
        self.assertTrue(self.loaded_spec)
        self.assertTrue(self.loaded_spec["experiment"])
        self.assertTrue(self.loaded_spec["experiment"]["sue"])
        self.assertTrue(self.loaded_spec["experiment"]["sue"]["required"])
        self.orc = KubernetesOrchestrator(experiment_config=self.loaded_spec)

    def tearDown(self) -> None:
        pass

    def test_it_reads_all_pods(self):
        self.assertTrue(self.orc.list_of_all_pods)
        self.assertGreaterEqual(len(self.orc.list_of_all_pods.items), 0)

    def test_it_reads_all_services(self):
        self.assertTrue(self.orc.list_of_all_services)
        self.assertGreaterEqual(len(self.orc.list_of_all_services.items), 0)

    def test_it_initializes_the_client(self):
        self.assertTrue(self.orc.kube_client)

    def test_it_erros_when_not_all_required_found(self):
        self.loaded_spec["experiment"]["sue"]["required"].append(
             {"namespace": "monitoring", "name": "not-running-service"}
        )
        with self.assertRaises(Exception):
            self.orc.ready()
        self.loaded_spec["experiment"]["sue"]["required"].pop()

    def test_it_checks_all_required(self):
        self.assertTrue(self.orc.ready())
