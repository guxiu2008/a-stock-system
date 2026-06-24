#!/usr/bin/env python3
import math
import pandas as pd


class FinancialAnalyzer:
    def __init__(self, conn, as_of_date: str):
        self.conn = conn
        self.as_of_date = as_of_date

    def analyze(self, ts_code: str) -> dict:
        reports = pd.read_sql_query(
            """
            SELECT end_date, ann_date, revenue, net_profit, ncf_from_oa, accounts_receiv,
                   total_assets, total_liab, roe, roe_waa, grossprofit_margin,
                   netprofit_margin, debt_to_assets
            FROM fact_financial_reports
            WHERE ts_code = ? AND (ann_date IS NULL OR ann_date <= ?)
            ORDER BY end_date DESC
            LIMIT 12
            """,
            self.conn,
            params=(ts_code, self.as_of_date),
        )
        dividends = pd.read_sql_query(
            """
            SELECT end_date, ann_date, cash_div_tax, payout_ratio, div_proc
            FROM fact_dividend_history
            WHERE ts_code = ? AND (ann_date IS NULL OR ann_date <= ?)
            ORDER BY end_date DESC
            LIMIT 8
            """,
            self.conn,
            params=(ts_code, self.as_of_date),
        )
        if reports.empty:
            return {
                "score": 0,
                "rating": "无数据",
                "hard_pass": False,
                "hard_reject": False,
                "notes": ["无可用财报数据"],
                "metrics": {},
            }
        reports = reports.drop_duplicates(subset=["end_date"]).copy()
        latest = reports.iloc[0]
        prev = reports.iloc[1] if len(reports) > 1 else None
        
        annual_reports = reports[reports["end_date"].astype(str).str.endswith("1231")]
        if not annual_reports.empty:
            latest_annual = annual_reports.iloc[0]
            annual_roe = self._num(latest_annual.get("roe")) or self._num(latest_annual.get("roe_waa"))
        else:
            annual_roe = None
        
        score = 0
        notes = []
        warnings = []
        metrics = self._metrics(latest, prev, reports, dividends, annual_roe)
        
        roe = metrics.get("roe")
        roe_annual = metrics.get("roe_annual")
        end_date = str(latest.get("end_date", ""))
        is_quarterly = len(end_date) >= 6 and end_date[4:6] in ["03", "06", "09"]
        
        if roe is None:
            notes.append("ROE缺失")
        else:
            if roe_annual is not None:
                roe_display = f"全年{roe_annual:.2f}%"
                effective_roe = roe_annual
            elif is_quarterly:
                roe_annualized = roe * 4
                roe_display = f"单季{roe:.2f}%（年化{roe_annualized:.1f}%)"
                effective_roe = min(roe_annualized, roe * 2)
            else:
                roe_display = f"{roe:.2f}%"
                effective_roe = roe
            
            if effective_roe >= 15:
                score += 18
                notes.append(f"ROE {roe_display}：盈利能力优秀")
            elif effective_roe >= 10:
                score += 14
                notes.append(f"ROE {roe_display}：盈利能力良好")
            elif effective_roe >= 5:
                score += 10
                notes.append(f"ROE {roe_display}：盈利能力稳定")
            elif effective_roe > 0:
                score += 5
                warnings.append(f"ROE {roe_display}：偏弱")
            else:
                warnings.append(f"ROE {roe_display}：亏损或净资产收益为负")
        
        revenue_yoy = metrics.get("revenue_yoy")
        if revenue_yoy is not None:
            if revenue_yoy >= 20:
                score += 14
                notes.append(f"营收同比 {revenue_yoy:+.2f}%：增长强")
            elif revenue_yoy >= 5:
                score += 10
                notes.append(f"营收同比 {revenue_yoy:+.2f}%：稳定增长")
            elif revenue_yoy >= -5:
                score += 5
                notes.append(f"营收同比 {revenue_yoy:+.2f}%：基本稳定")
            else:
                warnings.append(f"营收同比 {revenue_yoy:+.2f}%：下滑")
        profit_yoy = metrics.get("net_profit_yoy")
        if profit_yoy is not None:
            if profit_yoy >= 20:
                score += 14
                notes.append(f"净利同比 {profit_yoy:+.2f}%：增长强")
            elif profit_yoy >= 5:
                score += 10
                notes.append(f"净利同比 {profit_yoy:+.2f}%：稳定增长")
            elif profit_yoy >= -10:
                score += 5
                notes.append(f"净利同比 {profit_yoy:+.2f}%：基本稳定")
            else:
                warnings.append(f"净利同比 {profit_yoy:+.2f}%：明显下滑")
        gross_margin = metrics.get("gross_margin")
        if gross_margin is not None:
            if gross_margin >= 35:
                score += 10
                notes.append(f"毛利率 {gross_margin:.2f}%：较高")
            elif gross_margin >= 20:
                score += 7
                notes.append(f"毛利率 {gross_margin:.2f}%：正常")
            elif gross_margin >= 10:
                score += 3
                notes.append(f"毛利率 {gross_margin:.2f}%：偏低")
            else:
                warnings.append(f"毛利率 {gross_margin:.2f}%：较低")
        net_margin = metrics.get("net_margin")
        is_investment_type = gross_margin is not None and net_margin is not None and net_margin > gross_margin
        
        margin_explosion = False
        if gross_margin is not None and net_margin is not None and gross_margin >= 60 and net_margin >= 50:
            margin_explosion = True
            score += 25
            notes.append(f"毛利率{gross_margin:.2f}% + 净利率{net_margin:.2f}%：超高盈利水平，业绩核爆级表现！")
        elif gross_margin is not None and net_margin is not None and gross_margin >= 50 and net_margin >= 35:
            margin_explosion = True
            score += 20
            notes.append(f"毛利率{gross_margin:.2f}% + 净利率{net_margin:.2f}%：极高盈利能力，行业龙头定价权")
        
        if is_investment_type:
            score += 4
            notes.append(f"净利率 {net_margin:.2f}% > 毛利率 {gross_margin:.2f}%：投资收益主导（典型控股公司）")
        elif net_margin is not None and not margin_explosion:
            if net_margin >= 20:
                score += 14
                notes.append(f"净利率 {net_margin:.2f}%：非常优秀，行业龙头定价权")
            elif net_margin >= 15:
                score += 12
                notes.append(f"净利率 {net_margin:.2f}%：优秀，盈利能力强")
            elif net_margin >= 10:
                score += 9
                notes.append(f"净利率 {net_margin:.2f}%：良好")
            elif net_margin >= 5:
                score += 5
                notes.append(f"净利率 {net_margin:.2f}%：可接受")
            elif net_margin > 0:
                score += 2
                warnings.append(f"净利率 {net_margin:.2f}%：偏薄")
            else:
                warnings.append(f"净利率 {net_margin:.2f}%：亏损")
        metrics["is_investment_type"] = is_investment_type
        debt = metrics.get("debt_to_assets")
        if debt is not None:
            if debt <= 45:
                score += 10
                notes.append(f"资产负债率 {debt:.2f}%：压力较小")
            elif debt <= 65:
                score += 6
                notes.append(f"资产负债率 {debt:.2f}%：可控")
            elif debt <= 80:
                score += 2
                warnings.append(f"资产负债率 {debt:.2f}%：偏高")
            else:
                warnings.append(f"资产负债率 {debt:.2f}%：高风险")
        ocf_np = metrics.get("ocf_net_profit_ratio")
        if ocf_np is not None:
            if ocf_np >= 1.0:
                score += 12
                notes.append(f"经营现金流/净利 {ocf_np:.2f}：现金含量好")
            elif ocf_np >= 0.5:
                score += 6
                notes.append(f"经营现金流/净利 {ocf_np:.2f}：尚可")
            elif ocf_np >= 0:
                score += 2
                warnings.append(f"经营现金流/净利 {ocf_np:.2f}：偏弱")
            else:
                warnings.append(f"经营现金流为负：需警惕利润质量")
        ar_rev = metrics.get("receivable_revenue_ratio")
        if ar_rev is not None:
            if ar_rev <= 0.25:
                score += 6
                notes.append(f"应收/营收 {ar_rev:.2f}：回款压力较小")
            elif ar_rev <= 0.5:
                score += 3
                notes.append(f"应收/营收 {ar_rev:.2f}：需观察")
            else:
                warnings.append(f"应收/营收 {ar_rev:.2f}：回款压力偏高")
        div_years = metrics.get("dividend_years", 0)
        if div_years >= 3:
            score += 8
            notes.append(f"近年分红记录 {div_years} 次：股东回报较稳定")
        elif div_years > 0:
            score += 3
            notes.append(f"有分红记录 {div_years} 次")
        else:
            warnings.append("缺少近期分红记录")
        score = max(0, min(100, int(round(score))))
        hard_reject = self._hard_reject(metrics)
        hard_pass = score >= 60 and not hard_reject
        rating = "优秀" if score >= 80 else "良好" if score >= 65 else "一般" if score >= 50 else "偏弱" if score >= 35 else "高风险"
        out_notes = notes + warnings
        if hard_reject:
            out_notes.append("触发财务硬性风险：亏损/高负债/现金流恶化/营收利润明显下滑之一")
        return {
            "score": score,
            "rating": rating,
            "hard_pass": hard_pass,
            "hard_reject": hard_reject,
            "notes": out_notes[:12],
            "metrics": metrics,
        }

    def _metrics(self, latest, prev, reports, dividends, annual_roe=None):
        revenue = self._num(latest.get("revenue"))
        net_profit = self._num(latest.get("net_profit"))
        ocf = self._num(latest.get("ncf_from_oa"))
        receivable = self._num(latest.get("accounts_receiv"))
        current_roe = self._num(latest.get("roe")) or self._num(latest.get("roe_waa"))
        metrics = {
            "end_date": str(latest.get("end_date")),
            "ann_date": None if pd.isna(latest.get("ann_date")) else str(latest.get("ann_date")),
            "revenue": revenue,
            "net_profit": net_profit,
            "roe": annual_roe if annual_roe is not None else current_roe,
            "roe_quarterly": current_roe,
            "roe_annual": annual_roe,
            "gross_margin": self._num(latest.get("grossprofit_margin")),
            "net_margin": self._num(latest.get("netprofit_margin")),
            "debt_to_assets": self._num(latest.get("debt_to_assets")),
        }
        if prev is not None:
            metrics["revenue_yoy"] = self._growth(revenue, self._num(prev.get("revenue")))
            metrics["net_profit_yoy"] = self._growth(net_profit, self._num(prev.get("net_profit")))
        if net_profit and net_profit > 0 and ocf is not None:
            metrics["ocf_net_profit_ratio"] = ocf / net_profit
        elif ocf is not None:
            metrics["ocf_net_profit_ratio"] = -1 if ocf < 0 else None
        if revenue and revenue > 0 and receivable is not None:
            metrics["receivable_revenue_ratio"] = receivable / revenue
        metrics["dividend_years"] = int(dividends["end_date"].dropna().astype(str).str[:4].nunique()) if not dividends.empty else 0
        metrics["recent_reports"] = [
            {
                "end_date": str(r.get("end_date")),
                "revenue": self._round_money(self._num(r.get("revenue"))),
                "net_profit": self._round_money(self._num(r.get("net_profit"))),
                "roe": self._round_pct(self._num(r.get("roe"))),
                "debt_to_assets": self._round_pct(self._num(r.get("debt_to_assets"))),
            }
            for _, r in reports.head(5).iterrows()
        ]
        return {k: v for k, v in metrics.items() if v is not None}

    def _hard_reject(self, m: dict) -> bool:
        profit = m.get("net_profit")
        roe = m.get("roe")
        debt = m.get("debt_to_assets")
        profit_yoy = m.get("net_profit_yoy")
        revenue_yoy = m.get("revenue_yoy")
        ocf_np = m.get("ocf_net_profit_ratio")
        if profit is not None and profit < 0:
            return True
        if roe is not None and roe < 0:
            return True
        if debt is not None and debt > 85:
            return True
        if profit_yoy is not None and profit_yoy < -50 and revenue_yoy is not None and revenue_yoy < -20:
            return True
        if ocf_np is not None and ocf_np < -0.5:
            return True
        return False

    def _num(self, value):
        if value is None or pd.isna(value):
            return None
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        if math.isnan(v) or math.isinf(v):
            return None
        return v

    def _growth(self, current, previous):
        if current is None or previous is None or previous == 0:
            return None
        return (current - previous) / abs(previous) * 100

    def _round_money(self, value):
        if value is None:
            return None
        return round(value / 100000000, 2)

    def _round_pct(self, value):
        if value is None:
            return None
        return round(value, 2)
