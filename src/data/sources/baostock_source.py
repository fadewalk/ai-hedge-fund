import baostock as bs
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
from .base import DataSource, format_china_stock_code

class BaoStockSource(DataSource):
    """BaoStock数据源实现"""
    
    def __init__(self):
        # 初始化BaoStock
        bs.login()
    
    def __del__(self):
        # 确保退出登录
        bs.logout()
    
    def get_prices(self, ticker: str, start_date: str, end_date: str) -> List[Price]:
        """获取股票价格数据"""
        formatted_ticker = format_china_stock_code(ticker)
        
        # BaoStock的股票代码格式需要调整
        if '.SH' in formatted_ticker:
            bs_code = f"sh.{formatted_ticker.replace('.SH', '')}"
        else:
            bs_code = f"sz.{formatted_ticker.replace('.SZ', '')}"
            
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,volume",
            start_date=start_date,
            end_date=end_date,
            frequency="d"
        )
        
        prices = []
        while (data_list := rs.get_data()):
            for _, row in data_list.iterrows():
                price = Price(
                    time=row['date'],
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=int(float(row['volume']))
                )
                prices.append(price)
        
        return prices
    
    def get_financial_metrics(self, ticker: str, end_date: str, period: str = "annual", limit: int = 5) -> List[FinancialMetrics]:
        """获取财务指标数据"""
        formatted_ticker = format_china_stock_code(ticker)
        
        # BaoStock的股票代码格式需要调整
        if '.SH' in formatted_ticker:
            bs_code = f"sh.{formatted_ticker.replace('.SH', '')}"
        else:
            bs_code = f"sz.{formatted_ticker.replace('.SZ', '')}"
            
        # 获取季度业绩报表
        rs = bs.query_performance_express_report(bs_code, start_date=end_date)
        
        metrics = []
        while (data_list := rs.get_data()):
            for _, row in data_list.iterrows():
                metric = FinancialMetrics(
                    ticker=ticker,
                    report_period=row['statDate'],
                    period=period,
                    currency="CNY",
                    # 填充可用的财务指标
                    net_income=float(row['netProfit']) if 'netProfit' in row else None,
                    total_revenue=float(row['totalOperatingRevenue']) if 'totalOperatingRevenue' in row else None,
                    # 其他指标根据实际数据填充
                )
                metrics.append(metric)
                if len(metrics) >= limit:
                    break
        
        return metrics[:limit]
    
    def get_company_news(self, ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 1000) -> List[CompanyNews]:
        """获取公司新闻 - BaoStock不提供新闻数据，返回空列表"""
        return []
    
    def search_line_items(self, ticker: str, line_items: List[str], end_date: str, period: str = "ttm", limit: int = 10) -> List[LineItem]:
        """搜索财务数据项"""
        formatted_ticker = format_china_stock_code(ticker)
        
        # BaoStock的股票代码格式需要调整
        if '.SH' in formatted_ticker:
            bs_code = f"sh.{formatted_ticker.replace('.SH', '')}"
        else:
            bs_code = f"sz.{formatted_ticker.replace('.SZ', '')}"
            
        # 获取季度业绩报表
        rs = bs.query_performance_express_report(bs_code, start_date=end_date)
        
        items = []
        while (data_list := rs.get_data()):
            for _, row in data_list.iterrows():
                item_data = {
                    "ticker": ticker,
                    "report_period": row['statDate'],
                    "period": period,
                    "currency": "CNY"
                }
                
                # 将可用的财务数据项添加到结果中
                for item in line_items:
                    if item in row:
                        item_data[item] = float(row[item])
                
                items.append(LineItem(**item_data))
                if len(items) >= limit:
                    break
        
        return items[:limit]
    
    def get_insider_trades(self, ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 1000) -> List[InsiderTrade]:
        """获取内部交易数据"""
        formatted_ticker = format_china_stock_code(ticker)
        
        # BaoStock的股票代码格式需要调整
        if '.SH' in formatted_ticker:
            bs_code = f"sh.{formatted_ticker.replace('.SH', '')}"
        else:
            bs_code = f"sz.{formatted_ticker.replace('.SZ', '')}"
            
        rs = bs.query_history_trade_dates()
        trades = []
        
        # BaoStock提供的内部交易数据有限，这里返回空列表
        return trades
    
    def get_market_cap(self, ticker: str, end_date: str) -> Optional[float]:
        """获取市值数据"""
        formatted_ticker = format_china_stock_code(ticker)
        
        # BaoStock的股票代码格式需要调整
        if '.SH' in formatted_ticker:
            bs_code = f"sh.{formatted_ticker.replace('.SH', '')}"
        else:
            bs_code = f"sz.{formatted_ticker.replace('.SZ', '')}"
            
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,close,volume",
            start_date=end_date,
            end_date=end_date,
            frequency="d"
        )
        
        data_list = rs.get_data()
        if not data_list.empty:
            close_price = float(data_list['close'].iloc[0])
            # 获取总股本
            rs_stock = bs.query_stock_basic(code=bs_code)
            stock_data = rs_stock.get_data()
            if not stock_data.empty and 'totalShares' in stock_data.columns:
                total_shares = float(stock_data['totalShares'].iloc[0])
                return close_price * total_shares
        
        return None
