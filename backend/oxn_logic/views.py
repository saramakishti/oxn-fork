from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Experiment, ExperimentLock
from .serializers import ExperimentSerializer, ExperimentCreateSerializer
import yaml
import os
from pathlib import Path
from django.conf import settings
import logging
import json

# Create your views here.

def hello_world(request):
     return HttpResponse("Hello world")

logger = logging.getLogger(__name__)

class ExperimentViewSet(viewsets.ModelViewSet):
    queryset = Experiment.objects.all()
    serializer_class = ExperimentSerializer

    def create(self, request):
        try:
            serializer = ExperimentCreateSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Validation errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if another experiment is running
            lock = ExperimentLock.objects.first()
            if lock and lock.is_locked:
                return Response(
                    {"error": "Another experiment is currently running"}, 
                    status=status.HTTP_409_CONFLICT
                )
            
            try:
                # Create experiment record
                experiment = Experiment.objects.create(
                    name=serializer.validated_data.get('name', 'Unnamed Experiment'),
                    status='PENDING',
                    config_yaml=json.dumps(serializer.validated_data['config'])
                )
                
                try:
                    # Ensure base experiments directory exists
                    experiments_dir = Path(settings.OXN_DATA_DIR) / 'experiments'
                    experiments_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Create experiment-specific directory
                    base_path = experiments_dir / str(experiment.id)
                    base_path.mkdir(exist_ok=True)
                    
                    experiment.experiment_data_path = str(base_path / 'data')
                    experiment.benchmark_data_path = str(base_path / 'benchmark')
                    experiment.save()
                    
                except (OSError, PermissionError) as e:
                    logger.error(f"Failed to create directories: {e}")
                    experiment.delete()  # Clean up the DB record
                    return Response(
                        {"error": f"Failed to create experiment directories: {str(e)}"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                return Response(
                    ExperimentSerializer(experiment).data, 
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                logger.exception("Error creating experiment")
                return Response(
                    {"error": str(e)}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.exception("Unexpected error in create view")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        experiment = self.get_object()
        return Response({
            'status': experiment.status,
            'started_at': experiment.started_at,
            'completed_at': experiment.completed_at,
            'error_message': experiment.error_message
        })
