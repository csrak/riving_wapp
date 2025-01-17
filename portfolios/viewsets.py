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


class PortfolioViewSet(viewsets.ModelViewSet):
    """
    ViewSet for portfolio management operations.
    Handles portfolio creation, updates, and analysis.
    """
    serializer_class = PortfolioSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        """Filter portfolios by session key or user"""
        queryset = Portfolio.objects.all()

        if self.request.user.is_authenticated:
            # Show user's portfolios and public portfolios
            return queryset.filter(
                Q(user=self.request.user) | Q(is_public=True)
            )
        return queryset.filter(
            Q(session_key=self.request.session.session_key) | Q(is_public=True)
        )

    def perform_create(self, serializer):
        """Associate portfolio with session or user"""
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            if not self.request.session.session_key:
                self.request.session.save()
            serializer.save(session_key=self.request.session.session_key)

    @action(detail=False, methods=['post'])
    def upload_tickers(self, request):
        """Handle ticker file upload for portfolio creation"""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']
        if not file.name.endswith('.txt'):
            return Response(
                {'error': 'Only .txt files are supported'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            content = file.read().decode('utf-8')
            tickers = [line.strip() for line in content.splitlines() if line.strip()]
        except UnicodeDecodeError:
            return Response(
                {'error': 'Invalid file encoding'},
                status=status.HTTP_400_BAD_REQUEST
            )

        existing_securities = Security.objects.filter(ticker__in=tickers)
        found_tickers = existing_securities.values_list('ticker', flat=True)
        not_found = set(tickers) - set(found_tickers)

        return Response({
            'securities': SecuritySerializer(existing_securities, many=True).data,
            'not_found': list(not_found)
        })

    @action(detail=True)
    def calculate_metrics(self, request, pk=None):
        """Calculate portfolio metrics"""
        portfolio = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        try:
            metrics = portfolio.calculate_metrics(start_date, end_date)
            return Response(metrics)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


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