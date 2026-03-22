"""
每日数据同步主脚本
整合：数据拉取、质量验证、选股生成
每天15:30后自动运行
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 强制绕过系统代理，直连访问东方财富等数据源
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

from datetime import datetime
from database import db
from data_fetcher import DataFetcher
from data_validator import DataValidator
from stock_selector import StockSelector


def run_daily_sync():
    """运行每日同步任务"""
    print(f"\n{'#'*70}")
    print("#" + " "*68 + "#")
    print("#" + " A股量化投研 - 每日数据同步 ".center(68, " ") + "#")
    print("#" + f" 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".ljust(68) + "#")
    print("#" + " "*68 + "#")
    print(f"{'#'*70}\n")

    task_log_id = None

    try:
        # 1. 记录任务开始
        db.log_task('每日数据同步', 'running', '任务开始执行')

        # 2. 获取股票列表并过滤
        print("\n【步骤1】获取并过滤股票池...")
        fetcher = DataFetcher()

        all_stocks = fetcher.get_all_stocks()
        if all_stocks.empty:
            raise Exception("获取股票列表失败")

        filtered_stocks = fetcher.filter_stocks(all_stocks)
        if filtered_stocks.empty:
            raise Exception("过滤后股票池为空")

        # 保存股票基本信息
        count = fetcher.save_stock_basic(filtered_stocks)
        print(f"  股票池更新完成: {count} 只股票")

        stock_codes = filtered_stocks['code'].tolist()

        # 3. 拉取日线数据（近60天，每日增量）
        print("\n【步骤2】拉取日线数据...")
        daily_count = fetcher.fetch_all_daily_data(stock_codes, days=60)
        print(f"  日线数据更新完成: {daily_count} 条记录")

        # 财务数据由 finance_sync.py 每周单独跑，此处跳过

        # 5. 数据质量验证
        print("\n【步骤4】数据质量验证...")
        validator = DataValidator()
        validation_results = validator.run_all_validations()

        # 6. 运行选股引擎
        print("\n【步骤5】运行双引擎选股...")
        selector = StockSelector()
        signal_results = selector.run_all_engines()

        # 7. 任务完成
        print(f"\n{'='*70}")
        print("任务执行成功！")
        print(f"  - 股票池: {count} 只")
        print(f"  - 日线数据: {daily_count} 条")
        print(f"  - 生成信号: {signal_results['total']} 个")
        print(f"{'='*70}\n")

        db.log_task(
            '每日数据同步',
            'success',
            f'任务完成: {count}只股票, {daily_count}条日线, {signal_results["total"]}个信号（财务数据请单独运行finance_sync.py）',
            {
                'stock_count': count,
                'daily_count': daily_count,
                'signals': signal_results
            }
        )

        return True

    except Exception as e:
        error_msg = f"任务执行失败: {str(e)}"
        print(f"\n[失败] {error_msg}")

        db.log_task('每日数据同步', 'failed', error_msg)
        return False


if __name__ == '__main__':
    success = run_daily_sync()
    sys.exit(0 if success else 1)
