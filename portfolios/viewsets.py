# Add to viewsets.py
from rest_framework import viewsets
from .serializer import PortfolioSerializer, OptimizationScenario, OptimizationScenarioSerializer
from .models import Portfolio
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny # WHAT IS THIS
from rest_framework.parsers import JSONParser
from rest_framework.decorators import action
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import timedelta
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

    @action(detail=True)
    def analysis(self, request, pk=None):
        """Get portfolio analysis data including performance metrics"""
        portfolio = self.get_object()
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365)  # Default to 1 year

        if request.query_params.get('start_date'):
            start_date = parse_date(request.query_params['start_date'])
        if request.query_params.get('end_date'):
            end_date = parse_date(request.query_params['end_date'])

        analysis_data = {
            'portfolio': self.get_serializer(portfolio).data,
            'metrics': self.calculate_metrics(portfolio, start_date, end_date),
            'performance': self.calculate_performance(portfolio, start_date, end_date)
        }
        return Response(analysis_data)

    @action(detail=True, methods=['post'])
    def rebalance(self, request, pk=None):
        """Update portfolio security weights"""
        portfolio = self.get_object()
        securities_data = request.data.get('securities', [])

        for sec_data in securities_data:
            security = portfolio.securities.filter(id=sec_data['id']).first()
            if security:
                security.shares = sec_data.get('shares', security.shares)
                security.save()

        return Response(self.get_serializer(portfolio).data)

    def calculate_metrics(self, portfolio, start_date, end_date):
        """Calculate portfolio metrics"""
        securities = portfolio.securities.all()
        total_value = sum(s.shares * s.price for s in securities)

        return {
            'total_value': total_value,
            'number_of_securities': securities.count(),
            'last_updated': portfolio.updated_at,
            'date_range': {
                'start': start_date,
                'end': end_date
            }
        }

    def calculate_performance(self, portfolio, start_date, end_date):
        """Calculate portfolio performance metrics"""
        # This will be expanded with actual calculations
        return {
            'total_return': 0,
            'volatility': 0,
            'sharpe_ratio': 0
        }

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