"""
A股数据拉取模块 - 使用AKShare获取数据
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import db


class DataFetcher:
    """数据拉取器"""

    def __init__(self):
        self.db = db

    def get_all_stocks(self) -> pd.DataFrame:
        """获取全部A股列表"""
        print("正在获取全部A股列表...")
        try:
            # 获取股票列表
            df = ak.stock_zh_a_spot_em()
            print(f"获取到 {len(df)} 只股票")
            return df
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def filter_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤股票：
        - 排除ST/*ST股
        - 排除上市不足3年
        - 排除市值<30亿
        - 排除资产负债率>70%
        """
        print("开始过滤股票...")
        original_count = len(df)

        # 重命名列以便处理
        df = df.copy()

        # 1. 排除ST/*ST股
        if '名称' in df.columns:
            df = df[~df['名称'].str.contains('ST|退', na=False)]
            print(f"  - 排除ST股后: {len(df)} 只")

        # 2. 排除市值<30亿
        if '总市值' in df.columns:
            # AKShare市值单位是元，30亿 = 3e9
            df = df[df['总市值'] >= 3e9]
            print(f"  - 市值>=30亿: {len(df)} 只")
        elif '流通市值' in df.columns:
            df = df[df['流通市值'] >= 3e9]
            print(f"  - 流通市值>=30亿: {len(df)} 只")

        # 3. 获取上市日期并排除上市不足3年的
        three_years_ago = (datetime.now() - timedelta(days=3*365)).strftime('%Y%m%d')

        # 尝试获取每只股票的详细信息
        filtered_list = []
        for _, row in df.iterrows():
            code = row.get('代码', '')
            name = row.get('名称', '')
            if not code:
                continue

            try:
                # 获取个股信息
                stock_info = ak.stock_individual_info_em(symbol=code)
                if stock_info is not None and not stock_info.empty:
                    list_date = stock_info[stock_info['item'] == '上市时间']['value'].values
                    if len(list_date) > 0:
                        list_date_str = str(list_date[0])
                        if list_date_str >= three_years_ago:
                            continue  # 上市不足3年，跳过

                filtered_list.append({
                    'code': code,
                    'name': name,
                    'market_cap': row.get('总市值', row.get('流通市值', 0)) / 1e8,  # 转为亿
                    'industry': row.get('所属行业', ''),
                    'list_date': stock_info[stock_info['item'] == '上市时间']['value'].values[0] if stock_info is not None and not stock_info.empty else None
                })
            except Exception as e:
                # 如果获取不到详细信息，暂时保留
                filtered_list.append({
                    'code': code,
                    'name': name,
                    'market_cap': row.get('总市值', row.get('流通市值', 0)) / 1e8,
                    'industry': row.get('所属行业', ''),
                    'list_date': None
                })

        result_df = pd.DataFrame(filtered_list)
        print(f"  - 上市>3年后: {len(result_df)} 只")

        # 获取财务报表数据筛选资产负债率
        final_list = []
        for _, row in result_df.iterrows():
            code = row['code']
            try:
                # 获取主要财务指标
                finance_df = ak.stock_financial_analysis_indicator(symbol=code)
                if finance_df is not None and not finance_df.empty:
                    # 获取最新的资产负债率
                    debt_ratio = finance_df.get('资产负债率(%)', pd.Series([0])).iloc[0]
                    if isinstance(debt_ratio, (int, float)) and debt_ratio > 70:
                        continue  # 资产负债率>70%，跳过
                    row['debt_ratio'] = debt_ratio
                final_list.append(row)
            except Exception as e:
                # 获取不到财务数据，暂时保留
                final_list.append(row)

        result_df = pd.DataFrame(final_list)
        print(f"  - 资产负债率<=70%: {len(result_df)} 只")
        print(f"过滤完成: {original_count} -> {len(result_df)} 只")

        return result_df

    def save_stock_basic(self, df: pd.DataFrame) -> int:
        """保存股票基本信息到数据库"""
        if df.empty:
            return 0

        print(f"保存 {len(df)} 只股票基本信息...")

        # 转换数据格式
        records = []
        for _, row in df.iterrows():
            list_date = row.get('list_date')
            if list_date and isinstance(list_date, str):
                try:
                    list_date = datetime.strptime(list_date, '%Y%m%d').date()
                except:
                    list_date = None

            records.append({
                'code': row['code'],
                'name': row['name'],
                'industry': row.get('industry', ''),
                'list_date': list_date,
                'market_cap': row.get('market_cap', 0),
                'debt_ratio': row.get('debt_ratio', 0)
            })

        # 清空并重新插入
        try:
            self.db.execute("DELETE FROM stock_basic")
            insert_df = pd.DataFrame(records)
            count = self.db.insert_df(insert_df, 'stock_basic')
            print(f"成功保存 {count} 只股票")
            return count
        except Exception as e:
            print(f"保存股票基本信息失败: {e}")
            return 0

    def fetch_daily_data(self, code: str, days: int = 365) -> pd.DataFrame:
        """获取单只股票日线数据"""
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                    start_date=start_date, end_date=end_date, adjust="qfq")
            if df is not None and not df.empty:
                df = df.rename(columns={
                    '日期': 'trade_date',
                    '开盘': 'open',
                    '最高': 'high',
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '换手率': 'turnover'
                })
                df['code'] = code
                df['trade_date'] = pd.to_datetime(df['trade_date'])

                # 计算均线
                df['ma5'] = df['close'].rolling(window=5).mean()
                df['ma20'] = df['close'].rolling(window=20).mean()

                return df[['code', 'trade_date', 'open', 'high', 'low', 'close',
                          'volume', 'amount', 'turnover', 'ma5', 'ma20']]
        except Exception as e:
            print(f"获取 {code} 日线数据失败: {e}")

        return pd.DataFrame()

    def fetch_all_daily_data(self, codes: List[str], days: int = 365) -> int:
        """批量获取日线数据"""
        print(f"开始获取 {len(codes)} 只股票的日线数据...")
        total_count = 0

        for i, code in enumerate(codes):
            if i % 100 == 0:
                print(f"  进度: {i}/{len(codes)}")

            df = self.fetch_daily_data(code, days)
            if not df.empty:
                try:
                    # 使用INSERT OR IGNORE逻辑
                    self.db.insert_df(df, 'stock_daily', if_exists='append')
                    total_count += len(df)
                except Exception as e:
                    # 可能是重复数据，忽略错误
                    pass

        print(f"日线数据获取完成，共 {total_count} 条记录")
        return total_count

    def fetch_finance_data(self, code: str) -> pd.DataFrame:
        """获取单只股票财务数据"""
        try:
            df = ak.stock_financial_analysis_indicator(symbol=code)
            if df is not None and not df.empty:
                # 重命名列
                column_mapping = {
                    '报告日': 'report_date',
                    '净资产收益率(%)': 'roe',
                    '总资产报酬率(%)': 'roa',
                    '销售毛利率(%)': 'gross_margin',
                    '净利润(亿元)': 'net_profit',
                    '营业收入(亿元)': 'revenue',
                    '资产负债率(%)': 'debt_ratio',
                    '经营现金流净额(亿元)': 'operating_cash_flow',
                }

                # 获取PE/PB数据
                pe_df = ak.stock_a_indicator_lg(symbol=code)
                pe_ttm = None
                pb = None
                if pe_df is not None and not pe_df.empty:
                    pe_ttm = pe_df.get('市盈率(TTM)', pd.Series([None])).iloc[0]
                    pb = pe_df.get('市净率', pd.Series([None])).iloc[0]

                records = []
                for _, row in df.iterrows():
                    report_date = row.get('报告日', '')
                    if report_date:
                        try:
                            report_date = datetime.strptime(str(report_date), '%Y-%m-%d').date()
                        except:
                            report_date = None

                    # 计算现金流比率
                    net_profit = row.get('净利润(亿元)', 0)
                    cash_flow = row.get('经营现金流净额(亿元)', 0)
                    cash_flow_ratio = cash_flow / net_profit if net_profit and net_profit > 0 else 0

                    records.append({
                        'code': code,
                        'report_date': report_date,
                        'pe_ttm': pe_ttm,
                        'pb': pb,
                        'roe': row.get('净资产收益率(%)', None),
                        'net_profit': net_profit,
                        'cash_flow_ratio': cash_flow_ratio,
                        'revenue': row.get('营业收入(亿元)', None),
                        'gross_margin': row.get('销售毛利率(%)', None)
                    })

                return pd.DataFrame(records)
        except Exception as e:
            print(f"获取 {code} 财务数据失败: {e}")

        return pd.DataFrame()

    def fetch_all_finance_data(self, codes: List[str]) -> int:
        """批量获取财务数据"""
        print(f"开始获取 {len(codes)} 只股票的财务数据...")
        total_count = 0

        for i, code in enumerate(codes):
            if i % 50 == 0:
                print(f"  进度: {i}/{len(codes)}")

            df = self.fetch_finance_data(code)
            if not df.empty:
                try:
                    self.db.insert_df(df, 'stock_finance', if_exists='append')
                    total_count += len(df)
                except Exception as e:
                    pass

        print(f"财务数据获取完成，共 {total_count} 条记录")
        return total_count

    def get_hs300_daily(self, days: int = 365) -> pd.DataFrame:
        """获取沪深300指数数据"""
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        try:
            df = ak.index_zh_a_hist(symbol="000300", period="daily",
                                   start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                df = df.rename(columns={
                    '日期': 'date',
                    '收盘': 'close'
                })
                df['date'] = pd.to_datetime(df['date'])
                return df[['date', 'close']]
        except Exception as e:
            print(f"获取沪深300数据失败: {e}")

        return pd.DataFrame()


if __name__ == '__main__':
    fetcher = DataFetcher()

    # 测试获取股票列表
    stocks = fetcher.get_all_stocks()
    print(stocks.head())
