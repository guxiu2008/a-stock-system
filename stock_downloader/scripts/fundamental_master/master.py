#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务护城河数据工具 - 主类（优化版：批量股票代码模式）
"""

import datetime
from typing import Optional, Dict, Any, List
import json

import pandas as pd

from .database import FundamentalDatabase as FundamentalMasterDB
from .fetcher import FinancialDataFetcher


class FundamentalMaster:
    """财务护城河主类"""

    def __init__(self, db_path: str = "stock_data.db"):
        """
        初始化财务护城河工具

        Args:
            db_path: SQLite数据库文件路径
        """
        self.db = FundamentalMasterDB(db_path)
        self.fetcher = None

    def _ensure_fetcher(self):
        """确保数据获取器已初始化"""
        if self.fetcher is None:
            self.fetcher = FinancialDataFetcher(self.db.db_path)

    def update_financial_data(self, ts_code: str = None, 
                              start_date: str = None, 
                              end_date: str = None,
                              period: str = None,
                              batch_size: int = 100) -> int:
        """
        更新财务数据（核心优化：批量股票代码模式）

        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 报告期 (如 20231231)
            batch_size: 每批请求的股票数量，默认 100

        Returns:
            更新的记录数
        """
        import time
        self._ensure_fetcher()

        if ts_code:
            # 单只股票：直接获取并保存
            print(f"正在获取 {ts_code} 的财务数据...")
            df = self.fetcher.fetch_all_financial_data(ts_code, start_date, end_date, period)
            if df.empty:
                return 0
            count = self.db.save_financial_reports(df)
            self.db.log_update('financial_reports', count, 'success', start_date, end_date)
            print(f"财务数据更新完成，共 {count} 条记录")
            return count
        else:
            # 全量更新：批量股票代码模式（核心优化）
            stock_list = self.fetcher.fetch_stock_list()
            if not stock_list:
                print("没有股票需要更新")
                return 0

            print("=" * 60)
            print("开始批量更新财务数据（批量股票代码模式）")
            print(f"股票数量: {len(stock_list)}, 批次大小: {batch_size}")
            print("=" * 60)
            
            total_count = 0
            start_time = time.time()
            
            # 按报告期逐个更新（避免单次请求数据量过大）
            if period:
                periods = [period]
            else:
                # 默认只更新最近 1 年的 4 个报告期（避免耗时太长）
                now = datetime.datetime.now()
                periods = []
                for i in range(4):
                    # 计算报告期：从当前季度往前推
                    # 当前季度 = (now.month - 1) // 3
                    # 目标季度 = 当前季度 - i
                    target_quarter = (now.month - 1) // 3 - i
                    year = now.year + target_quarter // 4
                    quarter = target_quarter % 4
                    if quarter < 0:
                        quarter += 4
                        year -= 1
                    
                    # 季度末月份
                    month = (quarter + 1) * 3
                    end_day = 31 if month in [3, 12] else 30
                    
                    # 只添加已经结束的报告期（报告期结束日期 <= 当前日期）
                    period_date = datetime.datetime(year, month, end_day)
                    if period_date <= now:
                        periods.append(f"{year}{month:02d}{end_day:02d}")
                
                periods = list(set(periods))
                periods.sort(reverse=True)
            
            print(f"将更新以下报告期: {periods}")
            
            for p_idx, p in enumerate(periods, 1):
                print(f"\n--- 处理报告期 [{p_idx}/{len(periods)}]: {p} ---")
                
                # 先查询数据库，找出已存在该报告期数据的股票
                existing_stocks = self.db.get_existing_by_period(p)
                print(f"  数据库中已有 {len(existing_stocks)} 只股票的 {p} 数据")
                
                # 只对缺少数据的股票调用API
                missing_stocks = [ts for ts in stock_list if ts not in existing_stocks]
                print(f"  需要获取 {len(missing_stocks)} 只股票的数据")
                
                if not missing_stocks:
                    print(f"  该报告期数据已完整，跳过API调用")
                    continue
                
                # 批量获取缺少数据的股票（边获取边保存）
                for df in self.fetcher.fetch_by_stock_batch_generator(missing_stocks, period=p, batch_size=batch_size):
                    if not df.empty:
                        # 直接保存（因为我们只请求了缺少的数据）
                        count = self.db.save_financial_reports(df)
                        total_count += count
                        elapsed = time.time() - start_time
                        print(f"  报告期 {p} 保存 {count} 条记录，累计 {total_count} 条，耗时 {elapsed:.1f} 秒")
            
            elapsed = time.time() - start_time
            self.db.log_update('financial_reports', total_count, 'success', start_date, end_date)
            
            print("\n" + "=" * 60)
            print(f"批量更新完成！总记录数: {total_count}, 总耗时: {elapsed:.2f} 秒")
            print("=" * 60)
            
            return total_count

    def update_by_periods(self, periods: List[str], ts_code: str = None) -> int:
        """
        按多个报告期更新财务数据

        Args:
            periods: 报告期列表 (如 ['20231231', '20230930'])
            ts_code: 股票代码

        Returns:
            更新的总记录数
        """
        total_count = 0

        for period in periods:
            print(f"\n正在处理报告期: {period}")
            count = self.update_financial_data(ts_code=ts_code, period=period)
            total_count += count

        print(f"\n所有报告期更新完成，共 {total_count} 条记录")
        return total_count

    def update_last_10_years(self, ts_code: str = None) -> int:
        """
        更新过去10年的财务数据

        Args:
            ts_code: 股票代码

        Returns:
            更新的总记录数
        """
        current_date = datetime.datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        current_day = current_date.day
        periods = []

        # 生成过去10年的季度报告期，跳过未来日期
        for year in range(current_year - 10, current_year + 1):
            # 检查每个季度是否已过
            quarter_dates = [
                (3, 31, f"{year}0331"),
                (6, 30, f"{year}0630"),
                (9, 30, f"{year}0930"),
                (12, 31, f"{year}1231")
            ]
            
            for month, day, period_str in quarter_dates:
                # 如果是当前年份，检查日期是否已过
                if year == current_year:
                    if month > current_month or (month == current_month and day > current_day):
                        continue  # 跳过未来日期
                periods.append(period_str)

        return self.update_by_periods(periods, ts_code)

    # ==================== Agent 专属 Tool 接口 ====================

    def get_financial_health_score(self, ts_code: str) -> Dict[str, Any]:
        """
        获取财务健康评分 (Agent 接口)

        逻辑：获取过去 5 年的 ROE 均值、现金流覆盖率和最新负债率

        Args:
            ts_code: 股票代码

        Returns:
            健康报告字典
        """
        # 计算 5 年前的日期
        today = datetime.datetime.now()
        five_years_ago = today - datetime.timedelta(days=365 * 5)
        start_date = five_years_ago.strftime('%Y%m%d')

        df = self.db.get_financial_reports(ts_code=ts_code, start_date=start_date)

        if df.empty:
            return {
                "ts_code": ts_code,
                "status": "error",
                "message": "无可用财务数据"
            }

        # 只保留年报数据 (1231) 来计算年均值
        df_annual = df[df['end_date'].str.endswith('1231')].copy()

        if df_annual.empty:
            df_annual = df  # 如果没有年报，使用所有数据

        # 计算 ROE 均值
        roe_mean = df_annual['roe'].mean() if 'roe' in df_annual.columns and not df_annual['roe'].isna().all() else None

        # 计算现金流覆盖率 (ncf_from_oa / net_profit) 均值
        cashflow_coverage_mean = None
        if 'ncf_from_oa' in df_annual.columns and 'net_profit' in df_annual.columns:
            valid_data = df_annual[(df_annual['ncf_from_oa'].notna()) & (df_annual['net_profit'].notna()) & (df_annual['net_profit'] != 0)]
            if not valid_data.empty:
                coverage_ratios = valid_data['ncf_from_oa'] / valid_data['net_profit']
                cashflow_coverage_mean = coverage_ratios.mean()

        # 获取最新负债率
        latest_debt_to_assets = None
        if 'debt_to_assets' in df.columns and not df['debt_to_assets'].isna().all():
            latest_debt_to_assets = df.iloc[0]['debt_to_assets']

        # 获取最新报告期
        latest_end_date = df.iloc[0]['end_date'] if not df.empty else None

        return {
            "ts_code": ts_code,
            "status": "success",
            "latest_end_date": latest_end_date,
            "roe_mean_5y": round(roe_mean, 2) if roe_mean is not None else None,
            "cashflow_coverage_mean_5y": round(cashflow_coverage_mean, 2) if cashflow_coverage_mean is not None else None,
            "latest_debt_to_assets": round(latest_debt_to_assets, 2) if latest_debt_to_assets is not None else None,
            "summary": self._generate_health_summary(roe_mean, cashflow_coverage_mean, latest_debt_to_assets)
        }

    def _generate_health_summary(self, roe_mean: float, cashflow_coverage: float, debt_to_assets: float) -> str:
        """生成健康总结文本"""
        points = []

        if roe_mean is not None:
            if roe_mean >= 15:
                points.append(f"ROE 表现优秀，过去 5 年均值 {roe_mean:.2f}%")
            elif roe_mean >= 10:
                points.append(f"ROE 表现良好，过去 5 年均值 {roe_mean:.2f}%")
            else:
                points.append(f"ROE 表现一般，过去 5 年均值 {roe_mean:.2f}%")

        if cashflow_coverage is not None:
            if cashflow_coverage >= 1:
                points.append(f"现金流覆盖良好，均值 {cashflow_coverage:.2f}")
            else:
                points.append(f"现金流覆盖不足，均值 {cashflow_coverage:.2f}")

        if debt_to_assets is not None:
            if debt_to_assets < 40:
                points.append(f"负债率健康，当前 {debt_to_assets:.2f}%")
            elif debt_to_assets < 60:
                points.append(f"负债率适中，当前 {debt_to_assets:.2f}%")
            else:
                points.append(f"负债率较高，当前 {debt_to_assets:.2f}%")

        return "; ".join(points) if points else "数据不足，无法生成总结"

    def find_moat_stocks(self, ts_codes: List[str] = None, min_roe: float = 15) -> List[Dict[str, Any]]:
        """
        筛选具有护城河的股票 (Agent 接口)

        逻辑：筛选出 ROE 持续稳定在 min_roe 以上的股票

        Args:
            ts_codes: 股票代码列表，如果为 None 则从数据库中查找
            min_roe: 最低 ROE 要求，默认 15%

        Returns:
            符合条件的股票列表
        """
        # 计算 5 年前的日期
        today = datetime.datetime.now()
        five_years_ago = today - datetime.timedelta(days=365 * 5)
        start_date = five_years_ago.strftime('%Y%m%d')

        # 如果没有指定股票列表，获取数据库中有数据的所有股票
        if ts_codes is None:
            all_reports = self.db.get_financial_reports(start_date=start_date)
            if all_reports.empty:
                return []
            ts_codes = all_reports['ts_code'].unique().tolist()

        moat_stocks = []

        for ts_code in ts_codes:
            df = self.db.get_financial_reports(ts_code=ts_code, start_date=start_date)
            if df.empty or 'roe' not in df.columns:
                continue

            # 只保留年报数据
            df_annual = df[df['end_date'].str.endswith('1231')].copy()
            if df_annual.empty:
                df_annual = df

            # 检查 ROE 是否持续高于 min_roe
            valid_roe = df_annual[df_annual['roe'].notna()]['roe']
            if len(valid_roe) < 2:  # 至少需要 2 年数据
                continue

            # 计算 ROE 均值和稳定性
            roe_mean = valid_roe.mean()
            roe_min = valid_roe.min()

            # 要求：均值 >= min_roe 且 最低值 >= min_roe * 0.7 (允许一定波动)
            if roe_mean >= min_roe and roe_min >= min_roe * 0.7:
                health_score = self.get_financial_health_score(ts_code)
                moat_stocks.append({
                    "ts_code": ts_code,
                    "roe_mean_5y": round(roe_mean, 2),
                    "roe_min_5y": round(roe_min, 2),
                    "health_score": health_score
                })

        # 按 ROE 均值排序
        moat_stocks.sort(key=lambda x: x['roe_mean_5y'], reverse=True)
        return moat_stocks

    def detect_accounting_red_flags(self, ts_code: str) -> Dict[str, Any]:
        """
        检测财务预警信号 (Agent 接口)

        逻辑：如果"应收账款"增速远超"营业收入"增速，触发预警

        Args:
            ts_code: 股票代码

        Returns:
            预警信号字典
        """
        # 计算 3 年前的日期
        today = datetime.datetime.now()
        three_years_ago = today - datetime.timedelta(days=365 * 3)
        start_date = three_years_ago.strftime('%Y%m%d')

        df = self.db.get_financial_reports(ts_code=ts_code, start_date=start_date)

        if df.empty:
            return {
                "ts_code": ts_code,
                "status": "error",
                "message": "无可用财务数据"
            }

        red_flags = []
        warnings = []

        # 检查应收账款和营业收入
        if 'accounts_receiv' in df.columns and 'revenue' in df.columns:
            # 按 end_date 排序（升序）
            df_sorted = df.sort_values('end_date', ascending=True).copy()
            df_sorted = df_sorted.dropna(subset=['accounts_receiv', 'revenue'])

            if len(df_sorted) >= 2:
                # 计算最新一期和最早一期的增长率
                earliest = df_sorted.iloc[0]
                latest = df_sorted.iloc[-1]

                # 计算增长率，避免除零
                if earliest['revenue'] > 0:
                    revenue_growth = (latest['revenue'] - earliest['revenue']) / earliest['revenue'] * 100
                else:
                    revenue_growth = None

                if earliest['accounts_receiv'] > 0:
                    accounts_receiv_growth = (latest['accounts_receiv'] - earliest['accounts_receiv']) / earliest['accounts_receiv'] * 100
                else:
                    accounts_receiv_growth = None

                if revenue_growth is not None and accounts_receiv_growth is not None:
                    # 如果应收账款增速远超营收增速（超过 2 倍）
                    if accounts_receiv_growth > revenue_growth * 2 and accounts_receiv_growth > 20:
                        red_flags.append(
                            f"应收账款增速 ({accounts_receiv_growth:.1f}%) 远超营业收入增速 ({revenue_growth:.1f}%)，可能存在回款风险"
                        )
                    elif accounts_receiv_growth > revenue_growth * 1.5 and accounts_receiv_growth > 10:
                        warnings.append(
                            f"应收账款增速 ({accounts_receiv_growth:.1f}%) 高于营业收入增速 ({revenue_growth:.1f}%)，需关注"
                        )

        # 检查现金流和利润
        if 'ncf_from_oa' in df.columns and 'net_profit' in df.columns:
            # 计算最近一年的现金流覆盖率
            latest = df.iloc[0]
            if pd.notna(latest['ncf_from_oa']) and pd.notna(latest['net_profit']) and latest['net_profit'] != 0:
                cashflow_ratio = latest['ncf_from_oa'] / latest['net_profit']
                if cashflow_ratio < 0.5:
                    red_flags.append(
                        f"现金流覆盖不足，最近一期经营现金流仅为净利润的 {cashflow_ratio:.2f} 倍"
                    )

        return {
            "ts_code": ts_code,
            "status": "success",
            "red_flags": red_flags,
            "warnings": warnings,
            "has_red_flags": len(red_flags) > 0
        }

    # ==================== 主营业务构成 ====================

    def update_revenue_segments(self, ts_code: str = None, period: str = None,
                                batch_size: int = 100) -> int:
        """
        批量更新主营业务构成数据

        Args:
            ts_code: 股票代码（单只或逗号分隔多只）
            period: 报告期 (如 20231231)
            batch_size: 每批请求的股票数量

        Returns:
            更新的记录数
        """
        import time
        self._ensure_fetcher()

        if ts_code:
            print(f"正在获取 {ts_code} 的主营业务构成...")
            df = self.fetcher.fetch_mainbz(ts_code, period=period)
            if df.empty:
                return 0
            count = self.db.save_revenue_segments(df)
            print(f"主营业务构成更新完成，共 {count} 条记录")
            return count

        stock_list = self.fetcher.fetch_stock_list()
        if not stock_list:
            print("没有股票需要更新")
            return 0

        if period:
            periods = [period]
        else:
            now = datetime.datetime.now()
            periods = []
            for i in range(4):
                target_quarter = (now.month - 1) // 3 - i
                year = now.year + target_quarter // 4
                quarter = target_quarter % 4
                if quarter < 0:
                    quarter += 4
                    year -= 1
                month = (quarter + 1) * 3
                end_day = 31 if month in [3, 12] else 30
                period_date = datetime.datetime(year, month, end_day)
                if period_date <= now:
                    periods.append(f"{year}{month:02d}{end_day:02d}")
            periods = list(set(periods))
            periods.sort(reverse=True)

        print("=" * 60)
        print("开始批量更新主营业务构成")
        print(f"股票数量: {len(stock_list)}, 报告期: {periods}")
        print("=" * 60)

        total_count = 0
        start_time = time.time()

        for p_idx, p in enumerate(periods, 1):
            print(f"\n--- 处理报告期 [{p_idx}/{len(periods)}]: {p} ---")

            existing_stocks = self.db.get_existing_segments_by_period(p)
            print(f"  数据库中已有 {len(existing_stocks)} 只股票的 {p} 主营业务数据")

            missing_stocks = [ts for ts in stock_list if ts not in existing_stocks]
            print(f"  需要获取 {len(missing_stocks)} 只股票的数据")

            if not missing_stocks:
                print(f"  该报告期数据已完整，跳过API调用")
                continue

            for df in self.fetcher.fetch_mainbz_batch_generator(missing_stocks, period=p,
                                                                  batch_size=batch_size):
                if not df.empty:
                    count = self.db.save_revenue_segments(df)
                    total_count += count
                    elapsed = time.time() - start_time
                    print(f"  报告期 {p} 保存 {count} 条记录，累计 {total_count} 条，耗时 {elapsed:.1f} 秒")

        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print(f"主营业务构成批量更新完成！总记录数: {total_count}, 总耗时: {elapsed:.2f} 秒")
        print("=" * 60)

        return total_count

    def get_revenue_segments(self, ts_code: str, end_date: str = None,
                             bz_type: str = None) -> pd.DataFrame:
        """
        查询主营业务构成

        Args:
            ts_code: 股票代码
            end_date: 报告期 (如 20231231)
            bz_type: 类型过滤 (P=产品, I=行业, R=地区)

        Returns:
            主营业务构成DataFrame
        """
        return self.db.get_revenue_segments(ts_code=ts_code, end_date=end_date, bz_type=bz_type)

    def analyze_revenue_structure(self, ts_code: str) -> Dict[str, Any]:
        """
        分析收入结构质量 (Agent 接口)

        评估维度：
        - 收入集中度（第一大业务占比）
        - 多元化程度（业务线数量）
        - 各业务毛利率分布

        Args:
            ts_code: 股票代码

        Returns:
            收入结构分析结果
        """
        df = self.db.get_revenue_segments(ts_code=ts_code)
        if df.empty:
            return {
                "ts_code": ts_code,
                "status": "error",
                "message": "无主营业务构成数据"
            }

        latest_date = df['end_date'].max()
        latest_data = df[df['end_date'] == latest_date].copy()

        result = {
            "ts_code": ts_code,
            "status": "success",
            "end_date": latest_date,
            "bz_types": {},
        }

        for bz_type in ['P', 'I', 'R']:
            type_data = latest_data[latest_data['bz_type'] == bz_type]
            if type_data.empty:
                continue

            total_sales = type_data['bz_sales'].sum()
            if total_sales <= 0:
                continue

            type_data = type_data.copy()
            type_data['sales_pct'] = type_data['bz_sales'] / total_sales * 100
            type_data['gross_margin'] = type_data.apply(
                lambda r: (r['bz_profit'] / r['bz_sales'] * 100) if r['bz_sales'] and r['bz_sales'] > 0 else None,
                axis=1
            )

            items = []
            for _, row in type_data.sort_values('bz_sales', ascending=False).iterrows():
                item = {
                    "item": row['bz_item'],
                    "sales": round(row['bz_sales'] / 100000000, 2),
                    "profit": round(row['bz_profit'] / 100000000, 2) if pd.notna(row.get('bz_profit')) else None,
                    "sales_pct": round(row['sales_pct'], 1),
                }
                if row.get('gross_margin') is not None and pd.notna(row['gross_margin']):
                    item["gross_margin"] = round(row['gross_margin'], 1)
                items.append(item)

            top1_pct = items[0]['sales_pct'] if items else 0
            margins = [i['gross_margin'] for i in items if 'gross_margin' in i]

            type_label = {"P": "产品", "I": "行业", "R": "地区"}.get(bz_type, bz_type)
            result["bz_types"][type_label] = {
                "items": items,
                "count": len(items),
                "top1_concentration": round(top1_pct, 1),
                "avg_gross_margin": round(sum(margins) / len(margins), 1) if margins else None,
                "margin_range": [round(min(margins), 1), round(max(margins), 1)] if margins else None,
            }

        summary_parts = []
        for type_label, info in result["bz_types"].items():
            summary_parts.append(f"{type_label}: {info['count']}条业务线, 最大占比{info['top1_concentration']}%")
            if info['top1_concentration'] > 80:
                summary_parts[-1] += " ⚠️ 高度集中"
            if info.get('margin_range') and info['margin_range'][1] - info['margin_range'][0] > 40:
                summary_parts[-1] += " ⚠️ 毛利率差异大"

        result["summary"] = "; ".join(summary_parts) if summary_parts else "无有效数据"

        return result
