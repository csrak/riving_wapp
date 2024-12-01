from django.db.models import Model
from typing import Optional, TypeVar, Generic, List
from fin_data_cl.models import Security, FinancialReport, RiskComparison

T = TypeVar('T', bound=Model)


class FinancialRepository(Generic[T]):
    """Handles database operations for financial models."""

    def __init__(self, model: type[T]):
        self.model = model

    def get_by_criteria(self, security_id: int, year: int, month: int) -> Optional[T]:
        """Fetch financial data based on search criteria."""
        try:
            return self.model.objects.get(
                security_id=security_id,
                date__year=year,
                date__month=month
            )
        except self.model.DoesNotExist:
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