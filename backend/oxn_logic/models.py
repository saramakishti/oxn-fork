from django.db import models
import uuid

class Experiment(models.Model):
    """Represents a single experiment run"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=50, choices=[
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ])
    config_yaml = models.TextField()  # Store the experiment YAML config
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Paths to result files
    experiment_data_path = models.CharField(max_length=500, null=True, blank=True)
    benchmark_data_path = models.CharField(max_length=500, null=True, blank=True)
    
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

class ExperimentLock(models.Model):
    """Simple locking mechanism to prevent concurrent experiments"""
    is_locked = models.BooleanField(default=False)
    locked_by = models.UUIDField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
