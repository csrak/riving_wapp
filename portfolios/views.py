# portfolios/views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Portfolio, Position
from .serializers import PortfolioSerializer, PositionSerializer
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Portfolio
from .serializers import PortfolioSerializer
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.core.exceptions import ValidationError

class PortfolioManagementView(LoginRequiredMixin, TemplateView):
    template_name = 'portfolios/management.html'


class PortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def add_position(self, request, pk=None):
        """Add a position to portfolio"""
        portfolio = self.get_object()
        serializer = PositionSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(portfolio=portfolio)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_position(self, request, pk=None):
        """Update existing position"""
        try:
            position = Position.objects.get(
                id=request.data.get('position_id'),
                portfolio__user=request.user
            )
            serializer = PositionSerializer(
                position,
                data=request.data,
                partial=True
            )

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Position.DoesNotExist:
            return Response(
                {'detail': 'Position not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def remove_position(self, request, pk=None):
        """Remove position from portfolio"""
        try:
            position = Position.objects.get(
                id=request.data.get('position_id'),
                portfolio__user=request.user
            )
            position.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Position.DoesNotExist:
            return Response(
                {'detail': 'Position not found'},
                status=status.HTTP_404_NOT_FOUND
            )
@login_required
@require_http_methods(["POST"])
def create_portfolio(request):
    try:
        data = json.loads(request.body)
        portfolio = Portfolio.objects.create(
            user=request.user,
            name=data.get('name'),
            description=data.get('description', ''),
            is_public=data.get('is_public', False)
        )
        return JsonResponse({
            'id': portfolio.id,
            'name': portfolio.name,
            'description': portfolio.description
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# portfolios/views.py
class PortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioSerializer
    #permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user).order_by('id')

    @action(detail=True, methods=['post'])
    def add_position(self, request, pk=None):
        portfolio = self.get_object()
        security_id = request.data.get('security_id')
        shares = request.data.get('shares')
        average_price = request.data.get('average_price')

        position = Position.objects.create(
            portfolio=portfolio,
            security_id=security_id,
            shares=shares,
            average_price=average_price
        )

        return Response(PositionSerializer(position).data)

    @action(detail=True, methods=['post'])
    def update_position(self, request, pk=None):
        position_id = request.data.get('position_id')
        position = Position.objects.get(id=position_id, portfolio__user=request.user)
        position.shares = request.data.get('shares', position.shares)
        position.average_price = request.data.get('average_price', position.average_price)
        position.save()

        return Response(PositionSerializer(position).data)