# fin_data_cl/utils/fin_data_ops.py
from django.db.models import Model
from typing import Optional, TypeVar, Generic, List
from fin_data_cl.models import Security, FinancialReport, RiskComparison
import logging

T = TypeVar('T', bound=Model)

logger = logging.getLogger(__name__)

class FinancialRepository(Generic[T]):
    """Handles database operations for financial models."""

    def __init__(self, model: type[T]):
        self.model = model

    # Repository Class

    def get_by_criteria(self, security_id: int, year: int, month: int) -> Optional[T]:
        try:
            logger.debug(f"Fetching data for security_id={security_id}, year={year}, month={month}")
            queryset = self.model.objects.filter(
                security_id=security_id,
                date__year=year,
                date__month=month
            )
            logger.debug(f"Constructed Query: {queryset.query}")
            result = queryset.first()
            logger.debug(f"Query Result: {result}")
            logger.debug(f"Query parameters: security_id={security_id}, year={year}, month={month}")
            logger.debug(f"Found records: {queryset.count()}")
            return result
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}", exc_info=True)
            return None

    def get_years_for_security(self, security_id: int) -> List[int]:
        """Get all available years for a security."""
        dates = self.model.objects.filter(
            security_id=security_id
        ).dates('date', 'month', order='DESC')
        return sorted(set(date.year for date in dates), reverse=True)

    def get_months_for_year(self, security_id: int, year: int) -> List[int]:
        """Get available months for a security in a specific year."""
        dates = self.model.objects.filter(
            security_id=security_id,
            date__year=year
        ).dates('date', 'month', order='DESC')
        return [date.month for date in dates]

    def get_securities_for_exchange(self, exchange_id: int) -> List[dict]:
        """Get all active securities for an exchange."""
        securities = Security.objects.filter(
            exchange_id=exchange_id,
            is_active=True
        )
        return [
            {"id": security.id, "name": security.name}
            for security in securities
        ]
