#!/usr/bin/env python3
import json
import os
import pathlib
import re
import subprocess
import time
from urllib.parse import urlparse


class NewsVerifier:
    def __init__(self, python_bin: str = None, script_path: str = None, cache_path: str = None, ttl_hours: int = 24):
        self.python_bin = python_bin or os.getenv("PYTHON_BIN", "/workspace/stock_downloader/venv/bin/python")
        default_script = pathlib.Path(__file__).resolve().parents[3] / "tavily-search" / "scripts" / "tavily_search.py"
        self.script_path = script_path or os.getenv("TAVILY_SEARCH_SCRIPT", str(default_script))
        self.cache_path = pathlib.Path(cache_path or os.getenv("A_STOCK_NEWS_CACHE", "/tmp/a_stock_news_cache.json"))
        self.ttl = ttl_hours * 3600
        self.cache = self._load_cache()

    def analyze(self, pick: dict, financial: dict = None, max_results: int = 4) -> dict:
        name = pick.get("name") or ""
        code = pick.get("ts_code") or ""
        industry = pick.get("industry") or ""
        if not self._available():
            return {
                "available": False,
                "score": 50,
                "confidence": "未联网",
                "summary": "未配置 Tavily 或搜索脚本不可用，跳过实时新闻验证",
                "positive": [],
                "negative": [],
                "risk_flags": ["未完成实时新闻验证"],
                "sources": [],
            }
        queries = [
            f"{name} {code} 最新 公告 业绩 合同 风险",
            f"{name} {industry} 政策 订单 合作方 公告",
        ]
        all_results = []
        for q in queries:
            all_results.extend(self._search(q, max_results=max_results).get("results", []))
        all_results = self._dedupe(all_results)
        return self._score(name, code, industry, all_results, financial or {})

    def save_cache(self):
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _available(self):
        return pathlib.Path(self.script_path).exists() and bool(os.getenv("TAVILY_API_KEY") or (pathlib.Path.home() / ".opencode" / ".env").exists())

    def _search(self, query: str, max_results: int = 4) -> dict:
        key = query.strip()
        now = time.time()
        cached = self.cache.get(key)
        if cached and now - cached.get("ts", 0) <= self.ttl:
            return cached.get("data", {"results": []})
        try:
            proc = subprocess.run(
                [self.python_bin, self.script_path, "--query", query, "--max-results", str(max_results), "--format", "raw"],
                check=False,
                capture_output=True,
                text=True,
                timeout=45,
            )
            if proc.returncode != 0:
                data = {"query": query, "results": [], "error": proc.stderr.strip()[:300]}
            else:
                data = json.loads(proc.stdout)
        except Exception as e:
            data = {"query": query, "results": [], "error": str(e)[:300]}
        self.cache[key] = {"ts": now, "data": data}
        return data

    def _score(self, name: str, code: str, industry: str, results: list, financial: dict) -> dict:
        score = 50
        positive = []
        negative = []
        risk_flags = []
        sources = []
        domains = set()
        official_hits = 0
        company_hits = 0
        partner_hits = 0
        catalyst_hits = 0
        metrics = financial.get("metrics", {}) if financial else {}
        for r in results:
            title = (r.get("title") or "").strip()
            content = (r.get("content") or "").strip()
            url = r.get("url") or ""
            text = f"{title} {content}"
            domain = urlparse(url).netloc.lower()
            if domain:
                domains.add(domain)
            source_score = self._source_score(domain, title, content)
            score += source_score
            if source_score >= 10:
                official_hits += 1
            if name and name in text:
                company_hits += 1
                score += 2
            if self._has_partner_signal(text):
                partner_hits += 1
                score += 3
            if self._has_catalyst(text):
                catalyst_hits += 1
                score += 3
                positive.append(self._shorten(title or content))
            if self._has_risk(text):
                score -= 8
                negative.append(self._shorten(title or content))
            sources.append({
                "title": title,
                "url": url,
                "domain": domain,
                "snippet": self._shorten(content, 100),
                "source_score": source_score,
            })
        if len(domains) >= 3:
            score += 8
        elif len(domains) == 1 and sources:
            score -= 5
            risk_flags.append("新闻来源单一")
        if official_hits == 0 and sources:
            score -= 6
            risk_flags.append("未找到明显官方公告来源")
        if company_hits >= 2:
            score += 5
        if partner_hits > 0:
            score += 5
            positive.append("存在合作/订单/中标类线索，需优先核对公告原文")
        if catalyst_hits == 0 and sources:
            risk_flags.append("未发现明确新增催化剂")
        score += self._financial_consistency(metrics, positive, negative, risk_flags)
        score = max(0, min(100, int(round(score))))
        confidence = "高" if score >= 75 else "中" if score >= 55 else "低" if sources else "无新闻"
        summary = self._summary(confidence, official_hits, len(domains), catalyst_hits, len(negative), financial)
        return {
            "available": True,
            "score": score,
            "confidence": confidence,
            "summary": summary,
            "positive": self._unique(positive)[:5],
            "negative": self._unique(negative)[:5],
            "risk_flags": self._unique(risk_flags)[:6],
            "sources": sources[:8],
        }

    def _financial_consistency(self, metrics, positive, negative, risk_flags):
        delta = 0
        revenue_yoy = metrics.get("revenue_yoy")
        profit_yoy = metrics.get("net_profit_yoy")
        ocf_np = metrics.get("ocf_net_profit_ratio")
        debt = metrics.get("debt_to_assets")
        if revenue_yoy is not None and profit_yoy is not None:
            if revenue_yoy > 5 and profit_yoy > 5:
                delta += 6
                positive.append("财报增长与正面新闻具备一定一致性")
            elif revenue_yoy < -10 and profit_yoy < -20:
                delta -= 10
                negative.append("历史营收/净利下滑，需警惕利好新闻兑现难度")
                risk_flags.append("财报趋势与利好叙事可能不匹配")
        if ocf_np is not None and ocf_np < 0.3:
            delta -= 5
            risk_flags.append("现金流质量偏弱，订单/增长新闻需确认回款能力")
        if debt is not None and debt > 70:
            delta -= 5
            risk_flags.append("负债率偏高，扩张或合作新闻需关注融资压力")
        return delta

    def _source_score(self, domain: str, title: str, content: str) -> int:
        official_domains = ["cninfo.com.cn", "sse.com.cn", "szse.cn", "neeq.com.cn", "cs.com.cn"]
        mainstream = ["stcn.com", "cnstock.com", "证券时报", "中国证券报", "上海证券报", "证券日报", "财联社"]
        text = f"{title} {content}"
        if any(d in domain for d in official_domains):
            return 12
        if "公告" in title or "公告" in content[:200]:
            return 10
        if any(x in domain or x in text for x in mainstream):
            return 6
        if any(x in text for x in ["披露", "交易所", "投资者关系"]):
            return 4
        if any(x in text for x in ["股吧", "论坛", "传闻", "网传"]):
            return -6
        return 1

    def _has_catalyst(self, text: str) -> bool:
        return any(x in text for x in ["中标", "订单", "合同", "合作", "增持", "回购", "业绩增长", "预增", "政策支持", "产能", "新品", "并购", "重组"])

    def _has_partner_signal(self, text: str) -> bool:
        return any(x in text for x in ["合作方", "签约", "战略合作", "供应商", "客户", "联合", "中标", "采购"])

    def _has_risk(self, text: str) -> bool:
        return any(x in text for x in ["立案", "处罚", "问询函", "减持", "亏损", "下滑", "终止", "违约", "诉讼", "冻结", "退市", "商誉减值", "风险提示"])

    def _summary(self, confidence, official_hits, domain_count, catalyst_hits, negative_count, financial):
        parts = [f"新闻可信度{confidence}"]
        parts.append(f"官方/公告线索{official_hits}条")
        parts.append(f"独立来源{domain_count}个")
        parts.append(f"催化剂线索{catalyst_hits}条")
        if negative_count:
            parts.append(f"风险新闻{negative_count}条")
        if financial:
            parts.append(f"财务评分{financial.get('score', 0)}/100")
        return "，".join(parts)

    def _dedupe(self, results):
        seen = set()
        out = []
        for r in results:
            key = r.get("url") or r.get("title")
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(r)
        return out

    def _load_cache(self):
        try:
            if self.cache_path.exists():
                return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _unique(self, items):
        seen = set()
        out = []
        for x in items:
            if not x or x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    def _shorten(self, text: str, n: int = 80):
        text = re.sub(r"\s+", " ", text or "").strip()
        return text if len(text) <= n else text[:n] + "..."
