"""
数据质量验证模块
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database import db
import random


class DataValidator:
    """数据质量验证器"""

    def __init__(self):
        self.db = db

    def validate_roe_data(self, sample_size: int = 50, years: int = 3) -> dict:
        """
        随机抽取股票检查ROE数据完整性
        - 随机抽取50只股票
        - 检查近3年ROE数据
        - 缺失率>20%记录警告
        """
        print(f"\n{'='*60}")
        print("数据质量验证：ROE数据完整性检查")
        print(f"{'='*60}")

        # 获取所有股票代码
        all_codes_df = self.db.query("SELECT code FROM stock_basic")
        if all_codes_df.empty:
            return {'status': 'error', 'message': 'stock_basic表为空'}

        all_codes = all_codes_df['code'].tolist()

        # 随机抽取
        sample_size = min(sample_size, len(all_codes))
        sampled_codes = random.sample(all_codes, sample_size)
        print(f"随机抽取 {sample_size} 只股票进行检查")

        # 计算近3年的报告期数量（通常每年4个季度）
        expected_reports = years * 4
        threshold_missing = 0.2  # 20%缺失阈值

        results = []
        high_missing_stocks = []

        for code in sampled_codes:
            # 查询近3年的财务数据
            three_years_ago = (datetime.now() - timedelta(days=years*365)).strftime('%Y-%m-%d')

            sql = """
            SELECT COUNT(*) as report_count,
                   COUNT(roe) as roe_count,
                   AVG(roe) as avg_roe
            FROM stock_finance
            WHERE code = :code AND report_date >= :start_date
            """
            result = self.db.query_one(sql, {'code': code, 'start_date': three_years_ago})

            if result:
                report_count = result.get('report_count', 0) or 0
                roe_count = result.get('roe_count', 0) or 0

                missing_rate = (report_count - roe_count) / report_count if report_count > 0 else 1.0

                stock_info = self.db.query_one(
                    "SELECT name FROM stock_basic WHERE code = :code",
                    {'code': code}
                )
                stock_name = stock_info.get('name', 'Unknown') if stock_info else 'Unknown'

                results.append({
                    'code': code,
                    'name': stock_name,
                    'report_count': report_count,
                    'roe_count': roe_count,
                    'missing_rate': missing_rate,
                    'avg_roe': result.get('avg_roe', 0)
                })

                if missing_rate > threshold_missing:
                    high_missing_stocks.append({
                        'code': code,
                        'name': stock_name,
                        'missing_rate': f"{missing_rate*100:.1f}%"
                    })

        # 计算总体统计
        total_stocks = len(results)
        avg_missing_rate = np.mean([r['missing_rate'] for r in results]) if results else 0

        # 输出结果
        print(f"\n检查结果汇总:")
        print(f"  检查股票数: {total_stocks}")
        print(f"  平均缺失率: {avg_missing_rate*100:.2f}%")
        print(f"  高缺失股票数(>20%): {len(high_missing_stocks)}")

        if high_missing_stocks:
            print(f"\n⚠️  ROE数据缺失率>20%的股票:")
            for stock in high_missing_stocks[:10]:  # 只显示前10个
                print(f"    {stock['code']} {stock['name']}: {stock['missing_rate']}")

            # 记录警告到task_log
            self.db.log_task(
                '数据质量验证',
                'warning' if len(high_missing_stocks) > 5 else 'success',
                f'ROE数据验证完成，{len(high_missing_stocks)}只股票缺失率>20%',
                {
                    'total_checked': total_stocks,
                    'high_missing_count': len(high_missing_stocks),
                    'avg_missing_rate': f"{avg_missing_rate*100:.2f}%"
                }
            )
        else:
            print(f"\n✅ 所有抽查股票ROE数据质量良好")
            self.db.log_task(
                '数据质量验证',
                'success',
                f'ROE数据验证完成，平均缺失率{avg_missing_rate*100:.2f}%',
                {'total_checked': total_stocks, 'avg_missing_rate': f"{avg_missing_rate*100:.2f}%"}
            )

        return {
            'status': 'success',
            'total_checked': total_stocks,
            'high_missing_count': len(high_missing_stocks),
            'avg_missing_rate': avg_missing_rate,
            'high_missing_stocks': high_missing_stocks
        }

    def validate_daily_data(self) -> dict:
        """验证日线数据完整性"""
        print(f"\n{'='*60}")
        print("数据质量验证：日线数据完整性检查")
        print(f"{'='*60}")

        # 检查最近5个交易日是否有数据
        sql = """
        SELECT code, COUNT(*) as days_count, MAX(trade_date) as last_date
        FROM stock_daily
        WHERE trade_date >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY code
        """
        recent_data = self.db.query(sql)

        if recent_data.empty:
            message = "最近7天无日线数据"
            print(f"⚠️  {message}")
            self.db.log_task('日线数据验证', 'warning', message)
            return {'status': 'warning', 'message': message}

        # 计算平均每个股票的数据天数
        avg_days = recent_data['days_count'].mean()
        print(f"  最近7天平均每个股票有 {avg_days:.1f} 个交易日数据")

        # 检查是否有股票缺失数据
        all_codes = self.db.query("SELECT COUNT(*) as count FROM stock_basic").iloc[0]['count']
        codes_with_data = len(recent_data)

        print(f"  股票池总数: {all_codes}")
        print(f"  有近期数据的股票: {codes_with_data}")

        if codes_with_data < all_codes * 0.9:
            message = f"日线数据覆盖率低: {codes_with_data}/{all_codes}"
            print(f"⚠️  {message}")
            self.db.log_task('日线数据验证', 'warning', message)
            return {'status': 'warning', 'message': message}

        print(f"✅ 日线数据完整性良好")
        self.db.log_task('日线数据验证', 'success',
                        f'数据完整，{codes_with_data}只股票有近期数据')

        return {'status': 'success', 'codes_with_data': codes_with_data}

    def validate_finance_data(self) -> dict:
        """验证财务数据完整性"""
        print(f"\n{'='*60}")
        print("数据质量验证：财务数据完整性检查")
        print(f"{'='*60}")

        sql = """
        SELECT
            COUNT(*) as total_records,
            COUNT(pe_ttm) as pe_count,
            COUNT(pb) as pb_count,
            COUNT(roe) as roe_count,
            COUNT(cash_flow_ratio) as cf_count
        FROM stock_finance
        WHERE report_date >= CURRENT_DATE - INTERVAL '1 year'
        """
        result = self.db.query_one(sql)

        if not result or result.get('total_records', 0) == 0:
            message = "近1年无财务数据"
            print(f"⚠️  {message}")
            self.db.log_task('财务数据验证', 'warning', message)
            return {'status': 'warning', 'message': message}

        total = result.get('total_records', 1)
        completeness = {
            'PE_TTM': result.get('pe_count', 0) / total,
            'PB': result.get('pb_count', 0) / total,
            'ROE': result.get('roe_count', 0) / total,
            '现金流比率': result.get('cf_count', 0) / total
        }

        print(f"  近1年财务数据记录数: {total}")
        print(f"  字段完整率:")
        for field, rate in completeness.items():
            print(f"    {field}: {rate*100:.1f}%")

        # 检查是否有字段缺失率过高
        low_completeness = [f for f, r in completeness.items() if r < 0.8]

        if low_completeness:
            message = f"以下字段完整率低于80%: {', '.join(low_completeness)}"
            print(f"⚠️  {message}")
            self.db.log_task('财务数据验证', 'warning', message, completeness)
            return {'status': 'warning', 'message': message, 'completeness': completeness}

        print(f"✅ 财务数据完整性良好")
        self.db.log_task('财务数据验证', 'success',
                        f'数据完整，共{total}条记录', completeness)

        return {'status': 'success', 'completeness': completeness}

    def run_all_validations(self) -> dict:
        """运行所有验证"""
        print(f"\n{'#'*60}")
        print("#" + " "*58 + "#")
        print("#" + " 数据质量验证开始 ".center(58, " ") + "#")
        print("#" + " "*58 + "#")
        print(f"{'#'*60}")

        results = {
            'roe_validation': self.validate_roe_data(),
            'daily_validation': self.validate_daily_data(),
            'finance_validation': self.validate_finance_data()
        }

        # 汇总
        warnings = sum(1 for r in results.values() if r.get('status') == 'warning')
        errors = sum(1 for r in results.values() if r.get('status') == 'error')

        print(f"\n{'='*60}")
        print("验证汇总:")
        print(f"  警告: {warnings} 项")
        print(f"  错误: {errors} 项")
        print(f"{'='*60}\n")

        return results


if __name__ == '__main__':
    validator = DataValidator()
    validator.run_all_validations()
