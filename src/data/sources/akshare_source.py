import akshare as ak
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

class AKShareSource(DataSource):
    """AKShare数据源实现"""
    
    def get_prices(self, ticker: str, start_date: str, end_date: str) -> List[Price]:
        """获取股票价格数据"""
        formatted_ticker = format_china_stock_code(ticker)
        
        # 获取股票日K线数据
        df = ak.stock_zh_a_hist(
            symbol=formatted_ticker.split('.')[0],
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', ''),
            adjust="qfq"  # 前复权
        )
        
        prices = []
        for _, row in df.iterrows():
            price = Price(
                time=row['日期'].strftime('%Y-%m-%d'),
                open=float(row['开盘']),
                high=float(row['最高']),
                low=float(row['最低']),
                close=float(row['收盘']),
                volume=int(row['成交量'])
            )
            prices.append(price)
        
        return prices
    
    def get_financial_metrics(self, ticker: str, end_date: str, period: str = "annual", limit: int = 5) -> List[FinancialMetrics]:
        """获取财务指标数据"""
        formatted_ticker = format_china_stock_code(ticker)
        code = formatted_ticker.split('.')[0]
        
        # 获取财务指标数据
        df = ak.stock_financial_analysis_indicator(symbol=code)
        
        metrics = []
        for _, row in df.head(limit).iterrows():
            metric = FinancialMetrics(
                ticker=ticker,
                report_period=row['日期'],
                period=period,
                currency="CNY",
                # 填充可用的财务指标
                price_to_earnings_ratio=float(row['市盈率']) if '市盈率' in row else None,
                price_to_book_ratio=float(row['市净率']) if '市净率' in row else None,
                return_on_equity=float(row['净资产收益率']) if '净资产收益率' in row else None,
                # 其他指标根据实际数据填充
            )
            metrics.append(metric)
        
        return metrics
    
    def get_company_news(self, ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 1000) -> List[CompanyNews]:
        """获取公司新闻"""
        formatted_ticker = format_china_stock_code(ticker)
        code = formatted_ticker.split('.')[0]
        
        # AKShare提供新浪财经新闻接口
        df = ak.stock_news_em(symbol=code)
        
        news = []
        for _, row in df.head(limit).iterrows():
            news_item = CompanyNews(
                ticker=ticker,
                title=row['新闻标题'],
                date=row['发布时间'],
                url=row['新闻链接'] if '新闻链接' in row else "",
                source="新浪财经",
                author="新浪财经",
                sentiment=None  # 情感分析需要单独处理
            )
            news.append(news_item)
        
        return news
    
    def search_line_items(self, ticker: str, line_items: List[str], end_date: str, period: str = "ttm", limit: int = 10) -> List[LineItem]:
        """搜索财务数据项"""
        formatted_ticker = format_china_stock_code(ticker)
        code = formatted_ticker.split('.')[0]
        
        # 获取财务报表数据
        df = ak.stock_financial_report_sina(symbol=code)
        
        items = []
        for _, row in df.head(limit).iterrows():
            item_data = {
                "ticker": ticker,
                "report_period": row['报告期'] if '报告期' in row else end_date,
                "period": period,
                "currency": "CNY"
            }
            
            # 将可用的财务数据项添加到结果中
            for item in line_items:
                if item in row:
                    item_data[item] = float(row[item])
            
            items.append(LineItem(**item_data))
        
        return items
    
    def get_insider_trades(self, ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 1000) -> List[InsiderTrade]:
        """获取内部交易数据"""
        formatted_ticker = format_china_stock_code(ticker)
        code = formatted_ticker.split('.')[0]
        
        # 获取高管持股变动数据
        df = ak.stock_em_executive_hold(symbol=code)
        
        trades = []
        for _, row in df.head(limit).iterrows():
            trade = InsiderTrade(
                ticker=ticker,
                name=row['股东名称'] if '股东名称' in row else "",
                title=row['职务'] if '职务' in row else "",
                transaction_date=row['变动日期'] if '变动日期' in row else "",
                transaction_shares=float(row['变动数量']) if '变动数量' in row else 0,
                shares_owned_after_transaction=float(row['持股数量']) if '持股数量' in row else 0,
                filing_date=row['公告日期'] if '公告日期' in row else "",
                security_title="A股"
            )
            trades.append(trade)
        
        return trades
    
    def get_market_cap(self, ticker: str, end_date: str) -> Optional[float]:
        """获取市值数据"""
        formatted_ticker = format_china_stock_code(ticker)
        code = formatted_ticker.split('.')[0]
        
        try:
            # 获取实时行情数据
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == code]
            
            if not stock_data.empty:
                return float(stock_data['总市值'].iloc[0]) * 10000  # 转换为元
        except Exception as e:
            print(f"获取市值数据失败: {str(e)}")
        
        return None
