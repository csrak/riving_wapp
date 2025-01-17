# Add to viewsets.py
from rest_framework import viewsets
from .serializer import PortfolioSerializer, OptimizationScenario, OptimizationScenarioSerializer
from .models import Portfolio
from fin_data_cl.serializers import SecuritySerializer
from fin_data_cl.models import Security
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Max, Q, DecimalField
from rest_framework.permissions import AllowAny # WHAT IS THIS
from rest_framework.parsers import JSONParser

class PortfolioViewSet(viewsets.ModelViewSet):
    """ViewSet for portfolio management operations."""
    serializer_class = PortfolioSerializer
    permission_classes = [AllowAny]  # Adjust according to your needs
    parser_classes = [JSONParser]  # Add this line to explicitly accept JSON

    def get_queryset(self):
        """Filter portfolios by session key or user."""
        queryset = Portfolio.objects.all()
        if self.request.user.is_authenticated:
            return queryset.filter(user=self.request.user)
        return queryset.filter(session_key=self.request.session.session_key)

    def create(self, request, *args, **kwargs):
        """Create a new portfolio with securities."""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except Exception as e:
            return Response(
                {'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        """Associate portfolio with session or user."""
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            if not self.request.session.session_key:
                self.request.session.save()
            serializer.save(session_key=self.request.session.session_key)


class OptimizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for portfolio optimization operations.
    Handles optimization scenarios and results.
    """
    serializer_class = OptimizationScenarioSerializer

    def get_queryset(self):
        """Filter optimization scenarios by session key or user"""
        queryset = OptimizationScenario.objects.all()
        if self.request.user.is_authenticated:
            return queryset.filter(user=self.request.user)
        return queryset.filter(session_key=self.request.session.session_key)

    def perform_create(self, serializer):
        """Associate optimization scenario with session or user"""
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            if not self.request.session.session_key:
                self.request.session.save()
            serializer.save(session_key=self.request.session.session_key)

    @action(detail=True, methods=['post'])
    def run_optimization(self, request, pk=None):
        """Run the optimization for a scenario"""
        scenario = self.get_object()

        try:
            # Optimization logic will be implemented here
            # For now, return a placeholder response
            return Response({'status': 'Optimization will be implemented'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )