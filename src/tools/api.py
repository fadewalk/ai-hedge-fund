import os
import pandas as pd
import requests
import tushare as ts
from datetime import datetime

from data.cache import get_cache
from data.models import (
    CompanyNews,
    CompanyNewsResponse,
    FinancialMetrics,
    FinancialMetricsResponse,
    Price,
    PriceResponse,
    LineItem,
    LineItemResponse,
    InsiderTrade,
    InsiderTradeResponse,
)

# Global cache instance
_cache = get_cache()

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

def get_prices(ticker: str, start_date: str, end_date: str) -> list[Price]:
    """Fetch price data from cache or API."""
    # Check cache first
    if cached_data := _cache.get_prices(ticker):
        # Filter cached data by date range and convert to Price objects
        filtered_data = [Price(**price) for price in cached_data if start_date <= price["time"] <= end_date]
        if filtered_data:
            return filtered_data

    # 处理A股数据
    if is_china_stock(ticker):
        formatted_ticker = format_china_stock_code(ticker)
        try:
            pro = ts.pro_api(os.getenv('TUSHARE_API_KEY'))
            # Tushare需要反转日期格式
            start = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m%d')
            end = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
            
            df = pro.daily(ts_code=formatted_ticker, start_date=start, end_date=end)
            if df is not None and not df.empty:
                prices = []
                for _, row in df.iterrows():
                    price = Price(
                        time=row['trade_date'],
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=int(row['vol'] * 100)  # Tushare的成交量单位是手(100股)
                    )
                    prices.append(price)
                
                # Cache the results
                _cache.set_prices(ticker, [p.model_dump() for p in prices])
                return prices
        except Exception as e:
            print(f"Error fetching A-share data for {ticker}: {str(e)}")
            return []

    # 如果不是A股，使用原有的API
    headers = {}
    if api_key := os.environ.get("FINANCIAL_DATASETS_API_KEY"):
        headers["X-API-KEY"] = api_key

    url = f"https://api.financialdatasets.ai/prices/?ticker={ticker}&interval=day&interval_multiplier=1&start_date={start_date}&end_date={end_date}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")

    # Parse response with Pydantic model
    price_response = PriceResponse(**response.json())
    prices = price_response.prices

    if not prices:
        return []

    # Cache the results as dicts
    _cache.set_prices(ticker, [p.model_dump() for p in prices])
    return prices

def get_financial_metrics(ticker: str, end_date: str, period="annual", limit=5) -> list[FinancialMetrics]:
    """获取财务指标数据"""
    if is_china_stock(ticker):
        formatted_ticker = format_china_stock_code(ticker)
        try:
            pro = ts.pro_api(os.getenv('TUSHARE_API_KEY'))
            # 转换日期格式
            end = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
            
            # 获取基础财务指标
            df_basic = pro.daily_basic(ts_code=formatted_ticker, trade_date=end)
            if df_basic is None or df_basic.empty:
                return []
            
            # 获取利润表
            df_income = pro.income(ts_code=formatted_ticker, period=period, limit=limit)
            
            # 获取资产负债表
            df_balancesheet = pro.balancesheet(ts_code=formatted_ticker, period=period, limit=limit)
            
            # 构建财务指标对象
            metrics = []
            for _, row in df_basic.iterrows():
                metric = FinancialMetrics(
                    ticker=ticker,
                    report_period=end_date,
                    period=period,
                    currency="CNY",
                    market_cap=float(row['total_mv']) * 10000,  # 转换为元
                    price_to_earnings_ratio=float(row['pe']) if 'pe' in row else None,
                    price_to_book_ratio=float(row['pb']) if 'pb' in row else None,
                    # 其他指标根据实际数据填充
                )
                metrics.append(metric)
            
            return metrics
            
        except Exception as e:
            print(f"Error fetching A-share financial metrics for {ticker}: {str(e)}")
            return []

    # 如果不是A股，使用原有的API
    headers = {}
    if api_key := os.environ.get("FINANCIAL_DATASETS_API_KEY"):
        headers["X-API-KEY"] = api_key

    params = {
        "ticker": ticker,
        "end_date": end_date,
        "period": period,
        "limit": limit,
    }
    
    response = requests.get(
        "https://api.financialdatasets.ai/fundamentals",
        headers=headers,
        params=params,
    )
    
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")

    data = response.json()
    response_model = FinancialMetricsResponse(**data)
    return response_model.financial_metrics

def get_company_news(ticker: str, end_date: str, start_date: str | None = None, limit: int = 1000) -> list[CompanyNews]:
    """获取公司新闻"""
    if is_china_stock(ticker):
        formatted_ticker = format_china_stock_code(ticker)
        try:
            pro = ts.pro_api(os.getenv('TUSHARE_API_KEY'))
            # 转换日期格式
            end = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
            start = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m%d') if start_date else None
            
            # 获取公司新闻
            df_news = pro.news(ts_code=formatted_ticker, start_date=start, end_date=end)
            if df_news is None or df_news.empty:
                return []
            
            news_list = []
            for _, row in df_news.iterrows():
                news = CompanyNews(
                    ticker=ticker,
                    title=row['title'],
                    author="Tushare",
                    source=row['src'] if 'src' in row else "Unknown",
                    date=row['datetime'],
                    url=row['url'] if 'url' in row else "",
                    sentiment=None
                )
                news_list.append(news)
            
            return news_list[:limit]
            
        except Exception as e:
            print(f"Error fetching A-share news for {ticker}: {str(e)}")
            return []

    # 如果不是A股，使用原有的API
    if cached_data := _cache.get_company_news(ticker):
        filtered_data = [CompanyNews(**news) for news in cached_data 
                        if (start_date is None or news["date"] >= start_date)
                        and news["date"] <= end_date]
        filtered_data.sort(key=lambda x: x.date, reverse=True)
        if filtered_data:
            return filtered_data

    headers = {}
    if api_key := os.environ.get("FINANCIAL_DATASETS_API_KEY"):
        headers["X-API-KEY"] = api_key

    url = f"https://api.financialdatasets.ai/news/?ticker={ticker}&end_date={end_date}"
    if start_date:
        url += f"&start_date={start_date}"
    url += f"&limit={limit}"
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")
    
    data = response.json()
    response_model = CompanyNewsResponse(**data)
    news = response_model.news
    
    if not news:
        return []

    _cache.set_company_news(ticker, [n.model_dump() for n in news])
    return news

def search_line_items(ticker: str, line_items: list[str], end_date: str, period: str = "ttm", limit: int = 10) -> list[LineItem]:
    """搜索财务数据项"""
    if is_china_stock(ticker):
        formatted_ticker = format_china_stock_code(ticker)
        try:
            pro = ts.pro_api(os.getenv('TUSHARE_API_KEY'))
            # 转换日期格式
            end = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
            
            # 获取财务指标
            df_financial = pro.fina_indicator(ts_code=formatted_ticker, period=period, limit=limit)
            if df_financial is None or df_financial.empty:
                return []
            
            results = []
            for _, row in df_financial.iterrows():
                item_data = {"ticker": ticker, "report_period": end_date, "period": period, "currency": "CNY"}
                for item in line_items:
                    if item in row:
                        item_data[item] = float(row[item])
                results.append(LineItem(**item_data))
            
            return results
            
        except Exception as e:
            print(f"Error fetching A-share line items for {ticker}: {str(e)}")
            return []

    # 如果不是A股，使用原有的API
    headers = {}
    if api_key := os.environ.get("FINANCIAL_DATASETS_API_KEY"):
        headers["X-API-KEY"] = api_key

    url = "https://api.financialdatasets.ai/financials/search/line-items"
    body = {
        "tickers": [ticker],
        "line_items": line_items,
        "end_date": end_date,
        "period": period,
        "limit": limit,
    }
    
    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")
    
    data = response.json()
    response_model = LineItemResponse(**data)
    return response_model.search_results[:limit]

def get_insider_trades(ticker: str, end_date: str, start_date: str | None = None, limit: int = 1000) -> list[InsiderTrade]:
    """获取内部交易数据"""
    if is_china_stock(ticker):
        formatted_ticker = format_china_stock_code(ticker)
        try:
            pro = ts.pro_api(os.getenv('TUSHARE_API_KEY'))
            # 转换日期格式
            end = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
            start = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m%d') if start_date else None
            
            # 获取高管持股变动
            df_stk_holdertrade = pro.stk_holdertrade(ts_code=formatted_ticker, start_date=start, end_date=end)
            if df_stk_holdertrade is None or df_stk_holdertrade.empty:
                return []
            
            trades = []
            for _, row in df_stk_holdertrade.iterrows():
                trade = InsiderTrade(
                    ticker=ticker,
                    issuer=row['ts_code'],
                    name=row['holder_name'],
                    title=row['holder_type'],
                    is_board_director=True if row['holder_type'] in ['董事', '监事', '高管'] else False,
                    transaction_date=row['ann_date'],
                    transaction_shares=float(row['change_vol']),
                    transaction_price_per_share=float(row['avg_price']) if 'avg_price' in row else None,
                    transaction_value=float(row['change_vol']) * float(row['avg_price']) if 'avg_price' in row else None,
                    shares_owned_before_transaction=float(row['before_share']),
                    shares_owned_after_transaction=float(row['after_share']),
                    security_title="A股",
                    filing_date=row['ann_date']
                )
                trades.append(trade)
            
            return trades[:limit]
            
        except Exception as e:
            print(f"Error fetching A-share insider trades for {ticker}: {str(e)}")
            return []

    # 如果不是A股，使用原有的API
    if cached_data := _cache.get_insider_trades(ticker):
        filtered_data = [InsiderTrade(**trade) for trade in cached_data 
                        if (start_date is None or (trade.get("transaction_date") or trade["filing_date"]) >= start_date)
                        and (trade.get("transaction_date") or trade["filing_date"]) <= end_date]
        filtered_data.sort(key=lambda x: x.transaction_date or x.filing_date, reverse=True)
        if filtered_data:
            return filtered_data

    headers = {}
    if api_key := os.environ.get("FINANCIAL_DATASETS_API_KEY"):
        headers["X-API-KEY"] = api_key

    url = f"https://api.financialdatasets.ai/insider-trades/?ticker={ticker}&filing_date_lte={end_date}"
    if start_date:
        url += f"&filing_date_gte={start_date}"
    url += f"&limit={limit}"
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")
    
    data = response.json()
    response_model = InsiderTradeResponse(**data)
    trades = response_model.insider_trades
    
    if not trades:
        return []

    _cache.set_insider_trades(ticker, [trade.model_dump() for trade in trades])
    return trades

def get_market_cap(ticker: str, end_date: str) -> float | None:
    """获取市值数据"""
    financial_metrics = get_financial_metrics(ticker, end_date)
    if not financial_metrics:
        return None
    return financial_metrics[0].market_cap

def prices_to_df(prices: list[Price]) -> pd.DataFrame:
    """Convert prices to a DataFrame."""
    df = pd.DataFrame([p.model_dump() for p in prices])
    df["Date"] = pd.to_datetime(df["time"])
    df.set_index("Date", inplace=True)
    numeric_cols = ["open", "close", "high", "low", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.sort_index(inplace=True)
    return df

def get_price_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取价格数据并转换为DataFrame"""
    prices = get_prices(ticker, start_date, end_date)
    return prices_to_df(prices)
