"""
双引擎选股逻辑模块
- 长线引擎：基于ROE和PE的价值投资
- 短线引擎：基于技术面的趋势交易
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import db


class StockSelector:
    """双引擎选股器"""

    # 仓位规则常量
    LONG_MAX_PER_STOCK = 2000  # 长线单只上限
    LONG_MAX_STOCKS = 5        # 长线最多5只
    SHORT_MAX_PER_STOCK = 3000 # 短线单只上限
    SHORT_MAX_STOCKS = 3       # 短线最多3只

    # 短线信号冷却时间（小时）
    SIGNAL_COOLDOWN_HOURS = 48

    def __init__(self):
        self.db = db

    def get_index_ma20(self, symbol: str = "000300") -> Optional[float]:
        """获取指数20日均线"""
        try:
            sql = """
            SELECT close FROM stock_daily
            WHERE code = :code
            ORDER BY trade_date DESC LIMIT 20
            """
            df = self.db.query(sql, {'code': symbol})
            if len(df) >= 20:
                return df['close'].mean()
        except Exception as e:
            print(f"获取指数MA20失败: {e}")
        return None

    def is_index_above_ma20(self) -> bool:
        """检查上证指数是否在20日均线之上"""
        # 使用沪深300代替上证指数
        sql = """
        SELECT close FROM (
            SELECT close FROM stock_daily
            WHERE code = '000300'
            ORDER BY trade_date DESC LIMIT 1
        ) t
        """
        latest = self.db.query_one(sql)
        if not latest:
            return True  # 默认允许

        ma20 = self.get_index_ma20('000300')
        if ma20 is None:
            return True

        return latest['close'] > ma20

    def check_recent_signal(self, code: str, signal_type: str, hours: int = 48) -> bool:
        """检查某股票是否在最近N小时内有信号"""
        sql = """
        SELECT COUNT(*) as count FROM signals
        WHERE code = :code
          AND signal_type = :signal_type
          AND created_at >= CURRENT_TIMESTAMP - (:hours * INTERVAL '1 hour')
        """
        result = self.db.query_one(sql, {'code': code, 'signal_type': signal_type, 'hours': hours})
        return (result.get('count', 0) or 0) > 0

    def get_stock_daily_data(self, code: str, days: int = 260) -> pd.DataFrame:
        """获取股票日线数据"""
        sql = """
        SELECT * FROM stock_daily
        WHERE code = :code
          AND trade_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
        ORDER BY trade_date DESC
        """
        return self.db.query(sql, {'code': code, 'days': days})

    def get_stock_finance_data(self, code: str, years: int = 5) -> pd.DataFrame:
        """获取股票财务数据"""
        sql = """
        SELECT * FROM stock_finance
        WHERE code = :code
          AND report_date >= CURRENT_DATE - (:years * INTERVAL '1 year')
        ORDER BY report_date DESC
        """
        return self.db.query(sql, {'code': code, 'years': years})

    def calculate_pe_percentile(self, code: str, years: int = 5) -> Optional[Dict]:
        """计算PE历史分位数"""
        finance_df = self.get_stock_finance_data(code, years)

        if finance_df.empty or 'pe_ttm' not in finance_df.columns:
            return None

        pe_series = finance_df['pe_ttm'].dropna()

        if len(pe_series) < 20:  # 需要至少20个数据点
            return {'sufficient': False, 'count': len(pe_series)}

        current_pe = pe_series.iloc[0]

        # 计算历史分位
        percentile_20 = np.percentile(pe_series, 20)
        percentile_80 = np.percentile(pe_series, 80)

        return {
            'sufficient': True,
            'current_pe': current_pe,
            'percentile_20': percentile_20,
            'percentile_80': percentile_80,
            'min_pe': pe_series.min(),
            'max_pe': pe_series.max(),
            'count': len(pe_series)
        }

    def check_roe_criteria(self, code: str) -> Dict:
        """检查ROE条件：连续3年ROE>15% 且 经营现金流/净利润>0.8"""
        finance_df = self.get_stock_finance_data(code, 4)  # 近4年数据

        if finance_df.empty:
            return {'passed': False, 'reason': '无财务数据'}

        # 获取年度数据（每年最后一个报告期）
        finance_df['year'] = pd.to_datetime(finance_df['report_date']).dt.year
        annual_data = finance_df.groupby('year').first()

        if len(annual_data) < 3:
            return {'passed': False, 'reason': f'仅{len(annual_data)}年数据'}

        # 检查最近3年ROE
        recent_3y = annual_data.head(3)
        roe_list = recent_3y['roe'].dropna().tolist()

        if len(roe_list) < 3:
            return {'passed': False, 'reason': 'ROE数据不足'}

        min_roe = min(roe_list)
        if min_roe <= 15:
            return {
                'passed': False,
                'reason': f'ROE不满足: 最低{min_roe:.2f}%',
                'roe_list': roe_list
            }

        # 检查现金流比率
        cf_ratios = recent_3y['cash_flow_ratio'].dropna().tolist()
        min_cf_ratio = min(cf_ratios) if cf_ratios else 0

        if min_cf_ratio <= 0.8:
            return {
                'passed': False,
                'reason': f'现金流比率不满足: 最低{min_cf_ratio:.2f}',
                'roe_list': roe_list,
                'cf_ratios': cf_ratios
            }

        return {
            'passed': True,
            'roe_list': roe_list,
            'cf_ratios': cf_ratios,
            'avg_roe': np.mean(roe_list)
        }

    def check_technical_signals(self, code: str) -> Dict:
        """检查技术面信号"""
        daily_df = self.get_stock_daily_data(code, 30)

        if len(daily_df) < 20:
            return {'has_signal': False, 'reason': '日线数据不足'}

        # 按日期升序排列
        daily_df = daily_df.sort_values('trade_date')

        latest = daily_df.iloc[-1]
        prev_5 = daily_df.iloc[-6:-1]  # 前5天

        # 检查成交量：当前成交量 > 前5日均量 * 2
        current_volume = latest['volume']
        avg_volume_5 = prev_5['volume'].mean()
        volume_spike = current_volume > avg_volume_5 * 2

        # 检查均线：股价突破20日均线
        price = latest['close']
        ma20 = daily_df['close'].rolling(window=20).mean().iloc[-1]
        ma5 = daily_df['close'].rolling(window=5).mean().iloc[-1]

        above_ma20 = price > ma20
        prev_price = daily_df.iloc[-2]['close'] if len(daily_df) > 1 else price
        prev_ma20 = daily_df['close'].rolling(window=20).mean().iloc[-2] if len(daily_df) > 1 else ma20

        # 突破20日均线（之前低于MA20，现在高于MA20）
        breakout_ma20 = (price > ma20) and (prev_price <= prev_ma20)

        return {
            'has_signal': volume_spike and above_ma20,
            'breakout_ma20': breakout_ma20,
            'volume_spike': volume_spike,
            'above_ma20': above_ma20,
            'price': price,
            'ma20': ma20,
            'ma5': ma5,
            'volume': current_volume,
            'avg_volume_5': avg_volume_5,
            'volume_ratio': current_volume / avg_volume_5 if avg_volume_5 > 0 else 0
        }

    def get_current_positions(self, signal_type: str) -> List[Dict]:
        """获取当前持仓"""
        sql = """
        SELECT * FROM positions
        WHERE position_type = :position_type
        """
        df = self.db.query(sql, {'position_type': signal_type})
        return df.to_dict('records') if not df.empty else []

    def calculate_position_amount(self, signal_type: str) -> float:
        """计算建议仓位金额"""
        positions = self.get_current_positions(signal_type)
        current_count = len(positions)

        if signal_type == '长线':
            max_stocks = self.LONG_MAX_STOCKS
            max_per_stock = self.LONG_MAX_PER_STOCK
        else:
            max_stocks = self.SHORT_MAX_STOCKS
            max_per_stock = self.SHORT_MAX_PER_STOCK

        if current_count >= max_stocks:
            return 0  # 已满仓

        return max_per_stock

    def save_signal(self, code: str, name: str, action: str,
                   signal_type: str, trigger_logic: str,
                   position_amount: float) -> bool:
        """保存信号到数据库"""
        try:
            # 计算过期时间
            expires_at = datetime.now() + timedelta(hours=self.SIGNAL_COOLDOWN_HOURS)

            sql = """
            INSERT INTO signals
            (code, name, action, signal_type, trigger_logic,
             position_amount, created_at, expires_at, status)
            VALUES
            (:code, :name, :action, :signal_type, :trigger_logic,
             :position_amount, CURRENT_TIMESTAMP, :expires_at, 'pending')
            """
            self.db.execute(sql, {
                'code': code,
                'name': name,
                'action': action,
                'signal_type': signal_type,
                'trigger_logic': trigger_logic,
                'position_amount': position_amount,
                'expires_at': expires_at
            })

            print(f"  生成信号: {code} {name} [{signal_type}-{action}] {trigger_logic}")
            return True

        except Exception as e:
            print(f"  保存信号失败: {e}")
            return False

    def run_long_term_engine(self) -> int:
        """
        长线引擎
        - 入池：连续3年ROE>15% 且 经营现金流/净利润>0.8
        - 买入：PE-TTM跌入近5年历史分位20%以下
        - 卖出：PE-TTM达到历史80%分位 或 ROE跌破10%
        """
        print(f"\n{'='*60}")
        print("长线引擎选股开始")
        print(f"{'='*60}")

        # 获取股票池
        stocks_df = self.db.query("SELECT code, name FROM stock_basic")
        if stocks_df.empty:
            print("股票池为空")
            return 0

        signal_count = 0

        for _, stock in stocks_df.iterrows():
            code = stock['code']
            name = stock['name']

            # 检查是否已在池中有信号
            if self.check_recent_signal(code, '长线'):
                continue

            # 检查ROE条件
            roe_check = self.check_roe_criteria(code)
            if not roe_check['passed']:
                continue

            # 检查PE分位数
            pe_data = self.calculate_pe_percentile(code, 5)

            if pe_data is None:
                # 数据不足，记录为「数据不足」
                continue

            if not pe_data.get('sufficient', False):
                # 历史PE数据不足，跳过
                continue

            current_pe = pe_data['current_pe']
            pe_20 = pe_data['percentile_20']
            pe_80 = pe_data['percentile_80']

            # 买入信号：PE < 20%分位
            if current_pe < pe_20:
                position = self.calculate_position_amount('长线')
                if position > 0:
                    trigger = f"PE-TTM({current_pe:.2f})<历史20%分位({pe_20:.2f})，ROE={roe_check['avg_roe']:.2f}%"
                    if self.save_signal(code, name, '买入', '长线', trigger, position):
                        signal_count += 1

            # 卖出信号：PE > 80%分位 或 ROE < 10%
            # 检查是否有持仓
            positions = self.get_current_positions('长线')
            position_codes = [p['code'] for p in positions]

            if code in position_codes:
                if current_pe > pe_80:
                    trigger = f"PE-TTM({current_pe:.2f})>历史80%分位({pe_80:.2f})"
                    if self.save_signal(code, name, '卖出', '长线', trigger, 0):
                        signal_count += 1
                elif roe_check['roe_list'][0] < 10:
                    trigger = f"ROE跌破10%: {roe_check['roe_list'][0]:.2f}%"
                    if self.save_signal(code, name, '卖出', '长线', trigger, 0):
                        signal_count += 1

        print(f"长线引擎生成 {signal_count} 个信号")
        return signal_count

    def run_short_term_engine(self) -> int:
        """
        短线引擎
        - 前置过滤：上证指数须在20日均线之上
        - 买入：股价突破20日均线 且 成交量>前5日均量×2
        - 止损：跌破5日均线 或 亏损≥5%
        - 止盈：涨幅达到10%
        - 同一股票48小时内不重复生成信号
        """
        print(f"\n{'='*60}")
        print("短线引擎选股开始")
        print(f"{'='*60}")

        # 前置过滤：检查指数
        if not self.is_index_above_ma20():
            print("上证指数在20日均线之下，暂停生成短线买入信号")
            return 0

        print("上证指数在20日均线之上，继续选股")

        # 获取股票池
        stocks_df = self.db.query("SELECT code, name FROM stock_basic")
        if stocks_df.empty:
            print("股票池为空")
            return 0

        signal_count = 0

        for _, stock in stocks_df.iterrows():
            code = stock['code']
            name = stock['name']

            # 检查48小时内是否有信号
            if self.check_recent_signal(code, '短线', self.SIGNAL_COOLDOWN_HOURS):
                continue

            # 检查技术面信号
            tech = self.check_technical_signals(code)

            if not tech['has_signal']:
                continue

            # 买入信号
            if tech['breakout_ma20'] and tech['volume_spike']:
                position = self.calculate_position_amount('短线')
                if position > 0:
                    trigger = f"突破MA20({tech['ma20']:.2f})，成交量放大{tech['volume_ratio']:.1f}倍"
                    if self.save_signal(code, name, '买入', '短线', trigger, position):
                        signal_count += 1

        # 检查止损止盈（基于持仓）
        positions = self.get_current_positions('短线')
        for pos in positions:
            code = pos['code']
            name = pos['name']
            avg_cost = pos['avg_cost']

            daily_df = self.get_stock_daily_data(code, 10)
            if len(daily_df) < 5:
                continue

            latest = daily_df.iloc[0]
            current_price = latest['close']
            ma5 = daily_df['close'].rolling(window=5).mean().iloc[0]

            # 计算盈亏率
            pnl_pct = (current_price - avg_cost) / avg_cost * 100

            if current_price < ma5:
                trigger = f"跌破5日均线({ma5:.2f})，当前{current_price:.2f}"
                if self.save_signal(code, name, '卖出', '短线', trigger, 0):
                    signal_count += 1
            elif pnl_pct <= -5:
                trigger = f"亏损达{pnl_pct:.2f}%，触发止损"
                if self.save_signal(code, name, '卖出', '短线', trigger, 0):
                    signal_count += 1
            elif pnl_pct >= 10:
                trigger = f"盈利达{pnl_pct:.2f}%，触发止盈"
                if self.save_signal(code, name, '卖出', '短线', trigger, 0):
                    signal_count += 1

        print(f"短线引擎生成 {signal_count} 个信号")
        return signal_count

    def run_all_engines(self) -> Dict:
        """运行所有选股引擎"""
        print(f"\n{'#'*60}")
        print("#" + " "*58 + "#")
        print("#" + " 双引擎选股启动 ".center(58, " ") + "#")
        print("#" + " "*58 + "#")
        print(f"{'#'*60}")

        long_signals = self.run_long_term_engine()
        short_signals = self.run_short_term_engine()

        total = long_signals + short_signals

        # 记录到日志
        self.db.log_task(
            '双引擎选股',
            'success',
            f'共生成 {total} 个信号（长线:{long_signals}，短线:{short_signals}）',
            {'long': long_signals, 'short': short_signals}
        )

        print(f"\n选股完成，共生成 {total} 个交易信号")

        return {
            'long_signals': long_signals,
            'short_signals': short_signals,
            'total': total
        }


if __name__ == '__main__':
    selector = StockSelector()
    selector.run_all_engines()
