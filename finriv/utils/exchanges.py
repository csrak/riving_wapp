from dataclasses import dataclass
from datetime import time


@dataclass
class TradingHours:
    """Represents trading hours for a stock exchange"""
    trading_start: time
    trading_end: time
    break_start: time = None
    break_end: time = None


@dataclass
class Exchange:
    """Represents a stock exchange with its trading information"""
    code: str
    name: str
    timezone: str
    trading_hours: TradingHours
    suffix: str = ''  # Symbol suffix (e.g., '.SN' for Santiago)

    def is_trading_time(self, current_time: time) -> bool:
        """Check if the exchange is currently open"""
        if self.trading_hours.break_start and self.trading_hours.break_end:
            return self.trading_hours.trading_start <= current_time < self.trading_hours.break_start or \
                   self.trading_hours.break_end <= current_time < self.trading_hours.trading_end
        return self.trading_hours.trading_start <= current_time < self.trading_hours.trading


class ExchangeRegistry:
    """Registry of all supported exchanges"""
    def __init__(self):
        self._exchanges = {}
        self._initialize_exchanges()

    def _initialize_exchanges(self):
        # Chile (Santiago Stock Exchange)
        self.register_exchange(Exchange(
            suffix='SN',
            code='SCL',
            name='Santiago Stock Exchange',
            timezone='America/Santiago',
            trading_hours=TradingHours(
                trading_start=time(9, 30),
                trading_end=time(16, 0)
            )
        ))
        # Add more exchanges as needed
        # Example: New York Stock Exchange
        self.register_exchange(Exchange(
            suffix='NYQ',
            code='NYSE',
            name='New York Stock Exchange',
            timezone='America/New_York',
            trading_hours=TradingHours(
                trading_start=time(9, 30),
                trading_end=time(16, 0)
            )
        ))
        self.register_exchange(Exchange(
            suffix='NMS',
            code='NASDAQ',
            name='NASDAQ',
            timezone='America/New_York',
            trading_hours=TradingHours(
                trading_start=time(9, 30),
                trading_end=time(16, 0)
            )
        ))
        self.register_exchange(Exchange(
            suffix='L',
            code='LSE',
            name='London Stock Exchange',
            timezone='Europe/London',
            trading_hours=TradingHours(
                trading_start=time(8, 0),
                trading_end=time(16, 30)
            )
        ))
        self.register_exchange(Exchange(
            suffix='T',
            code='TSE',
            name='Tokyo Stock Exchange',
            timezone='Asia/Tokyo',
            trading_hours=TradingHours(
                trading_start=time(9, 0),
                trading_end=time(15, 0)
            )
        ))
        self.register_exchange(Exchange(
            suffix='HK',
            code='HKEX',
            name='Hong Kong Stock Exchange',
            timezone='Asia/Hong_Kong',
            trading_hours=TradingHours(
                trading_start=time(9, 30),
                trading_end=time(16, 0)
            )
        ))
        self.register_exchange(Exchange(
            suffix='SH',
            code='SSE',
            name='Shanghai Stock Exchange',
            timezone='Asia/Shanghai',
            trading_hours=TradingHours(
                trading_start=time(9, 30),
                trading_end=time(15, 0)
            )
        ))
        self.register_exchange(Exchange(
            suffix='SZ',
            code='SZSE',
            name='Shenzhen Stock Exchange',
            timezone='Asia/Shanghai',
            trading_hours=TradingHours(
                trading_start=time(9, 30),
                trading_end=time(15, 0)
            )
        ))
        self.register_exchange(Exchange(
            suffix='AS',
            code='ASX',
            name='Australian Securities Exchange',
            timezone='Australia/Sydney',
            trading_hours=TradingHours(
                trading_start=time(10, 0),
                trading_end=time(16, 0)
            )
        ))
        self.register_exchange(Exchange(
            suffix='BR',
            code='BVSP',
            name='B3',
            timezone='America/Sao_Paulo',
            trading_hours=TradingHours(
                trading_start=time(10, 0),
                trading_end=time(17, 30)
            )
        ))
        self.register_exchange(Exchange(
            suffix='MX',
            code='BMV',
            name='Mexican Stock Exchange',
            timezone='America/Mexico_City',
            trading_hours=TradingHours(
                trading_start=time(8, 30),
                trading_end=time(15, 0)
            )
        ))
        self.register_exchange(Exchange(
            suffix='KS',
            code='KRX',
            name='Korea Exchange',
            timezone='Asia/Seoul',
            trading_hours=TradingHours(
                trading_start=time(9, 0),
                trading_end=time(15, 30)
            )
        ))
        self.register_exchange(Exchange(
            suffix='TW',
            code='TWSE',
            name='Taiwan Stock Exchange',
            timezone='Asia/Taipei',
            trading_hours=TradingHours(
                trading_start=time(9, 0),
                trading_end=time(13, 30)
            )
        ))
        self.register_exchange(Exchange(
            suffix='SI',
            code='SGX',
            name='Singapore Exchange',
            timezone='Asia/Singapore',
            trading_hours=TradingHours(
                trading_start=time(9, 0),
                trading_end=time(17, 0)
            )
        ))
        self.register_exchange(Exchange(
            suffix='JO',
            code='JSE',
            name='Johannesburg Stock Exchange',
            timezone='Africa/Johannesburg',
            trading_hours=TradingHours(
                trading_start=time(9, 0),
                trading_end=time(17, 0)
            )
        ))

    def register_exchange(self, exchange: Exchange):
        """Register a new exchange"""
        self._exchanges[exchange.code] = exchange

    def get_exchange(self, code: str) -> Exchange:
        """Get exchange by its code"""
        return self._exchanges.get(code)

    def get_all_exchanges(self):
        """Get all registered exchanges"""
        return self._exchanges.values()

    def get_exchange_by_suffix(self, suffix: str) -> Exchange:
        """Get exchange by its suffix"""
        for exchange in self._exchanges.values():
            if exchange.suffix == suffix:
                return exchange
        return None

    def get_exchange_by_exchange_name(self, name: str) -> Exchange:
        """Get exchange by its name"""
        for exchange in self._exchanges.values():
            if exchange.name == name:
                return exchange
        return None



