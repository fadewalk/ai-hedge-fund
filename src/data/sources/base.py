from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import pandas as pd

from data.models import (
    Price,
    CompanyNews,
    FinancialMetrics,
    LineItem,
    InsiderTrade
)

class DataSource(ABC):
    """数据源抽象基类"""
    
    @abstractmethod
    def get_prices(self, ticker: str, start_date: str, end_date: str) -> List[Price]:
        """获取股票价格数据"""
        pass
    
    @abstractmethod
    def get_financial_metrics(self, ticker: str, end_date: str, period: str = "annual", limit: int = 5) -> List[FinancialMetrics]:
        """获取财务指标数据"""
        pass
    
    @abstractmethod
    def get_company_news(self, ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 1000) -> List[CompanyNews]:
        """获取公司新闻"""
        pass
    
    @abstractmethod
    def search_line_items(self, ticker: str, line_items: List[str], end_date: str, period: str = "ttm", limit: int = 10) -> List[LineItem]:
        """搜索财务数据项"""
        pass
    
    @abstractmethod
    def get_insider_trades(self, ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 1000) -> List[InsiderTrade]:
        """获取内部交易数据"""
        pass
    
    @abstractmethod
    def get_market_cap(self, ticker: str, end_date: str) -> Optional[float]:
        """获取市值数据"""
        pass

class MarketType:
    """市场类型"""
    A_SHARE = "A_SHARE"  # A股
    US_STOCK = "US_STOCK"  # 美股

def is_china_stock(ticker: str) -> bool:
    """判断是否为A股代码"""
    if not ticker:
        return False
    # 支持带后缀(.SH/.SZ)和不带后缀的代码
    base_code = ticker.split('.')[0]
    return (
        len(base_code) == 6 
        and base_code.isdigit() 
        and (base_code.startswith(('6', '0', '3', '5', '9')))
    )

def format_china_stock_code(ticker: str) -> str:
    """格式化A股代码"""
    if '.' in ticker:  # 已经包含后缀
        return ticker
    if ticker.startswith(('6', '5', '9')):
        return f"{ticker}.SH"
    elif ticker.startswith(('0', '3')):
        return f"{ticker}.SZ"
    return ticker
