"""analyze_assessment — 系统性估值分析（8模块工作流）."""

import json
from datetime import datetime
from urllib.parse import quote
from tools.analysis import _ds, _extract_tables, _load_skill, _save_report, _REPORT_BASE, now_str


async def analyze_assessment(
    company_name: str,
    stock_code: str,
) -> str:
    """对A股上市公司进行系统性估值分析。

    执行8模块工作流：排雷 → 宏观 → 行业生命周期 → 多模型估值
    (DCF/PE/PEG/PB-ROE按生命周期自动选择) → 催化剂追踪 →
    安全边际(三重底) → 合规自检 → 进一步分析建议。
    输出结构化估值分析报告（Markdown格式），并保存到 reports/ 目录。
    分析框架来源：equity-research/stock-assessment skill。

    Args:
        company_name: 公司中文简称（如 "招商银行"）
        stock_code: 6位股票代码（如 "600036"）
    """
    try:
        # === A. 行情 + 排雷 + 安全边际 (mx-data) ===
        market_raw = _ds.mx_data.query(
            f"{company_name} 最新价 总市值 pe pb 总股本 股息率"
            f" 货币资金 有息负债 总资产 经营现金流 每股净资产"
            f" 大股东 质押比例"
        )
        market_text = json.dumps(_extract_tables(market_raw), ensure_ascii=False, indent=2)

        # === B. 财务 + 行业生命周期 (mx-data) ===
        fin_raw = _ds.mx_data.query(
            f"{company_name} 近五年 每股收益 净资产收益率 营收增长率"
            f" 净利润 毛利率 扣非净利润"
        )
        fin_text = json.dumps(_extract_tables(fin_raw), ensure_ascii=False, indent=2)

        # === C. 催化剂(解禁/分红) (mx-data) ===
        catalyst_raw = _ds.mx_data.query(
            f"{company_name} 限售股解禁 分红"
        )
        catalyst_text = json.dumps(_extract_tables(catalyst_raw), ensure_ascii=False, indent=2)

        # === D. 机构研报 (mx-search) ===
        research = _ds.search(
            f"{company_name} {stock_code} 机构 盈利预测 EPS 评级 研报"
        )
        research_text = json.dumps(research.get("items", [])[:15], ensure_ascii=False, indent=2)

        # === E. 宏观 + 行业 (mx-search) ===
        macro = _ds.search(
            "中国 10年期国债收益率 M2同比 工业增加值 "
            f"{company_name} 行业 增速 PE 2026年"
        )
        macro_text = json.dumps(macro.get("items", [])[:10], ensure_ascii=False, indent=2)

        user_prompt = f"""请分析以下公司的估值。

公司：{company_name}
股票代码：{stock_code}
当前日期：{now_str()}
base_year = {datetime.now().year - 1}, latest_year = {datetime.now().year}

=== 行情 + 排雷 ===
{market_text}

=== 历史财务 ===
{fin_text}

=== 催化剂(解禁/分红) ===
{catalyst_text}

=== 机构研报/盈利预测 ===
{research_text}

=== 宏观 + 行业 ===
{macro_text}

请严格按照分析框架输出完整的估值分析报告，必须包含全部模块：
排雷检测、宏观评估、行业生命周期判定、多模型估值(含目标价区间)、
安全边际(三重底)、催化剂追踪、进一步分析建议。"""

        report = _ds.generate_report(_load_skill("stock-assessment"), user_prompt)
        filename = _save_report(f"{company_name}_估值分析", report)
        return f"{report}\n\n---\n📥 报告下载: {_REPORT_BASE}/reports/{quote(filename, safe='._')}"
    except Exception as e:
        return f"分析失败: {e}"
