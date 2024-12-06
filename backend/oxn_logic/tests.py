from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
import json
from pathlib import Path
import yaml

class ExperimentAPITests(APITestCase):
    def setUp(self):
        # Path to experiments directory
        self.experiments_dir = Path(__file__).parent.parent.parent / 'experiments'
        
        # Load a valid experiment file for testing
        latest_yaml = self.experiments_dir / 'delay-90.yml'
        with open(latest_yaml) as f:
            self.valid_experiment = yaml.safe_load(f)

    def test_create_experiment_with_valid_config(self):
        """Test creating an experiment with valid configuration"""
        data = {
            'name': 'Test Experiment',
            'config': self.valid_experiment
        }
        
        response = self.client.post('/api/experiments/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Experiment')
        self.assertEqual(response.data['status'], 'PENDING')
