from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
import json
from pathlib import Path
import yaml
import os

class ExperimentAPITests(APITestCase):
    def setUp(self):
        # Get experiments directory from environment variable, with fallback
        experiments_path = os.getenv('OXN_EXPERIMENTS_DIR', str(Path(__file__).parent.parent.parent / 'experiments'))
        self.experiments_dir = Path(experiments_path)
        
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

    def test_create_experiment_with_invalid_config(self):
        """Test creating an experiment with invalid configuration"""
        data = {'name': 'Test Experiment', 'config': {'invalid': 'config'}}
        response = self.client.post('/api/experiments/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_experiment_when_another_is_running(self):
        """Test creating an experiment when another is running"""
        # Create an experiment
        self.test_create_experiment_with_valid_config()
        # Try to create another experiment
        response = self.client.post('/api/experiments/', self.valid_experiment, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
