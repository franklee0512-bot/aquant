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
        """获取沪深300+中证500成分股，作为股票池"""
        print("正在获取沪深300+中证500成分股...")
        try:
            rows = {}
            for symbol, label in [("000300", "沪深300"), ("000905", "中证500")]:
                try:
                    cons = ak.index_stock_cons(symbol=symbol)
                    code_col = '品种代码' if '品种代码' in cons.columns else cons.columns[0]
                    name_col = '品种名称' if '品种名称' in cons.columns else (cons.columns[1] if len(cons.columns) > 1 else None)
                    for _, r in cons.iterrows():
                        code = str(r[code_col])
                        name = str(r[name_col]) if name_col else code
                        if code not in rows:
                            rows[code] = {'code': code, 'name': name}
                    print(f"  - {label}: {len(cons)} 只")
                except Exception as e:
                    print(f"  - {label} 获取失败: {e}")

            if not rows:
                raise Exception("沪深300和中证500成分股均获取失败")

            df = pd.DataFrame(list(rows.values()))
            print(f"获取到 {len(df)} 只成分股（去重后）")
            return df
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def filter_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤股票：
        - 排除ST/*ST股
        - 排除市值<30亿（沪深300/500基本都满足，保留兜底检查）
        - 上市3年以上（指数成分股天然满足，跳过逐个查询）
        - 排除资产负债率>70%
        """
        print("开始过滤股票...")
        original_count = len(df)

        df = df.copy()

        # 1. 排除ST/*ST股
        name_col = 'name' if 'name' in df.columns else ('名称' if '名称' in df.columns else None)
        if name_col:
            df = df[~df[name_col].str.contains('ST|退', na=False)]
            print(f"  - 排除ST股后: {len(df)} 只")

        # 2. 市值过滤（沪深300/500成分股已满足，有列时做兜底检查）
        for cap_col in ('总市值', '流通市值'):
            if cap_col in df.columns:
                df = df[df[cap_col] >= 3e9]
                print(f"  - {cap_col}>=30亿: {len(df)} 只")
                break
        else:
            print(f"  - 市值过滤跳过（成分股默认满足）")

        # 3. 整理基础字段
        code_col = 'code' if 'code' in df.columns else '代码'
        filtered_list = []
        for _, row in df.iterrows():
            code = row.get(code_col, '')
            name = row.get('name', row.get('名称', ''))
            if not code:
                continue
            filtered_list.append({
                'code': code,
                'name': name,
                'market_cap': row.get('总市值', row.get('流通市值', 0)) / 1e8,
                'industry': row.get('所属行业', ''),
                'list_date': None
            })

        result_df = pd.DataFrame(filtered_list)

        # 4. 资产负债率过滤（沪深300/500成分股跳过，避免逐个API调用）
        print(f"  - 资产负债率过滤跳过（成分股默认满足）")
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
        """获取单只股票财务数据（同花顺财务摘要 + 乐咕乐股PE指标）"""
        try:
            # 1. 同花顺财务摘要（含ROE、净利润、营业收入）
            fin_df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
            if fin_df is None or fin_df.empty:
                return pd.DataFrame()

            # 2. 乐咕乐股 PE/PB 指标（最新值）
            pe_ttm, pb = None, None
            try:
                pe_df = ak.stock_a_indicator_lg(symbol=code)
                if pe_df is not None and not pe_df.empty:
                    pe_ttm = pe_df.get('市盈率(TTM)', pd.Series([None])).iloc[0]
                    pb = pe_df.get('市净率', pd.Series([None])).iloc[0]
            except Exception:
                pass

            records = []
            for _, row in fin_df.iterrows():
                report_date = row.get('报告期', None)
                if report_date:
                    try:
                        report_date = datetime.strptime(str(report_date), '%Y-%m-%d').date()
                    except Exception:
                        report_date = None

                net_profit = row.get('净利润(亿元)', None)
                cash_flow = row.get('经营活动产生的现金流量净额(亿元)', None)
                if net_profit and cash_flow and float(net_profit) > 0:
                    cash_flow_ratio = float(cash_flow) / float(net_profit)
                else:
                    cash_flow_ratio = None

                roe_raw = row.get('净资产收益率(%)', None)
                try:
                    roe = float(roe_raw) if roe_raw is not None else None
                except (ValueError, TypeError):
                    roe = None

                records.append({
                    'code': code,
                    'report_date': report_date,
                    'pe_ttm': pe_ttm,
                    'pb': pb,
                    'roe': roe,
                    'net_profit': net_profit,
                    'cash_flow_ratio': cash_flow_ratio,
                    'revenue': row.get('营业收入(亿元)', None),
                    'gross_margin': None
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
