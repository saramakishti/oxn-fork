from rest_framework import serializers
from .models import Experiment
import json
from pathlib import Path
from jsonschema import validate, ValidationError as JsonSchemaError

# Load schema once at module level
SCHEMA_PATH = Path(__file__).parent.parent / 'schemas' / 'experiment_schema.json'
with open(SCHEMA_PATH) as f:
    EXPERIMENT_SCHEMA = json.load(f)

class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = ['id', 'name', 'status', 'created_at', 'started_at', 
                 'completed_at', 'error_message']

class ExperimentCreateSerializer(serializers.Serializer):
    config = serializers.JSONField()  # Changed from CharField to JSONField
    name = serializers.CharField(required=False)

    def validate_config(self, value):
        """Validate config against JSON schema"""
        try:
            validate(instance=value, schema=EXPERIMENT_SCHEMA)
            return value
        except JsonSchemaError as e:
            raise serializers.ValidationError(f"Invalid experiment configuration: {str(e)}")