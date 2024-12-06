# fin_data_cl/utils/session_utils.py

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class FinancialSessionManager:
    """Manages session storage for financial search criteria."""

    def __init__(self, request, prefix: str):
        self.request = request
        self.prefix = prefix

    def save_to_session(self, exchange_id, security_id, year, month):
        """Save search criteria to session."""
        self.request.session[f'{self.prefix}-exchange'] = exchange_id
        self.request.session[f'{self.prefix}-security'] = security_id
        self.request.session[f'{self.prefix}-year'] = year
        self.request.session[f'{self.prefix}-month'] = month
        self.request.session.modified = True

    def get_from_session(self):
        """Retrieve search criteria from session."""
        return {
            'exchange': self.request.session.get(f'{self.prefix}-exchange'),
            'security': self.request.session.get(f'{self.prefix}-security'),
            'year': self.request.session.get(f'{self.prefix}-year'),
            'month': self.request.session.get(f'{self.prefix}-month'),
        }
