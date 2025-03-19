import os
import requests
import pandas as pd
from datetime import datetime
from typing import List, Optional

from data.models import (
    Price,
    CompanyNews,
    FinancialMetrics,
    LineItem,
    InsiderTrade
)
from .base import DataSource

class USStockSource(DataSource):
    """美股数据源实现"""
    
    def __init__(self):
        self.api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
        if not self.api_key:
            raise ValueError("FINANCIAL_DATASETS_API_KEY environment variable is not set")
    
    def _get_headers(self):
        return {"X-API-KEY": self.api_key}
    
    def get_prices(self, ticker: str, start_date: str, end_date: str) -> List[Price]:
        """获取股票价格数据"""
        url = f"https://api.financialdatasets.ai/prices/?ticker={ticker}&interval=day&interval_multiplier=1&start_date={start_date}&end_date={end_date}"
        
        response = requests.get(url, headers=self._get_headers())
        if response.status_code != 200:
            raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")
        
        data = response.json()
        return [Price(**price) for price in data.get("prices", [])]
    
    def get_financial_metrics(self, ticker: str, end_date: str, period: str = "annual", limit: int = 5) -> List[FinancialMetrics]:
        """获取财务指标数据"""
        url = "https://api.financialdatasets.ai/fundamentals"
        params = {
            "ticker": ticker,
            "end_date": end_date,
            "period": period,
            "limit": limit,
        }
        
        response = requests.get(url, headers=self._get_headers(), params=params)
        if response.status_code != 200:
            raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")
        
        data = response.json()
        return [FinancialMetrics(**metric) for metric in data.get("financial_metrics", [])]
    
    def get_company_news(self, ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 1000) -> List[CompanyNews]:
        """获取公司新闻"""
        url = f"https://api.financialdatasets.ai/news/?ticker={ticker}&end_date={end_date}"
        if start_date:
            url += f"&start_date={start_date}"
        url += f"&limit={limit}"
        
        response = requests.get(url, headers=self._get_headers())
        if response.status_code != 200:
            raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")
        
        data = response.json()
        return [CompanyNews(**news) for news in data.get("news", [])]
    
    def search_line_items(self, ticker: str, line_items: List[str], end_date: str, period: str = "ttm", limit: int = 10) -> List[LineItem]:
        """搜索财务数据项"""
        url = "https://api.financialdatasets.ai/financials/search/line-items"
        body = {
            "tickers": [ticker],
            "line_items": line_items,
            "end_date": end_date,
            "period": period,
            "limit": limit,
        }
        
        response = requests.post(url, headers=self._get_headers(), json=body)
        if response.status_code != 200:
            raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")
        
        data = response.json()
        return [LineItem(**item) for item in data.get("search_results", [])]
    
    def get_insider_trades(self, ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 1000) -> List[InsiderTrade]:
        """获取内部交易数据"""
        url = f"https://api.financialdatasets.ai/insider-trades/?ticker={ticker}&filing_date_lte={end_date}"
        if start_date:
            url += f"&filing_date_gte={start_date}"
        url += f"&limit={limit}"
        
        response = requests.get(url, headers=self._get_headers())
        if response.status_code != 200:
            raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")
        
        data = response.json()
        return [InsiderTrade(**trade) for trade in data.get("insider_trades", [])]
    
    def get_market_cap(self, ticker: str, end_date: str) -> Optional[float]:
        """获取市值数据"""
        metrics = self.get_financial_metrics(ticker, end_date)
        if not metrics:
            return None
        return metrics[0].market_cap
