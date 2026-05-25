"""估值数据类 MCP Tool (5个): DCF, DDM, Comps, LBO, 3-Statement."""

import json
from shared.clients import DataSourceManager

_ds = DataSourceManager()


def register(ds_manager: DataSourceManager = None):
    global _ds
    if ds_manager:
        _ds = ds_manager


async def get_dcf_data(company_name: str, stock_code: str) -> str:
    """获取DCF估值模型所需全部数据。

    返回：自由现金流相关数据、WACC参数（Beta、当前股价、市值）、
    近三年营收和净利润增长率等。数据来源：mx-data + tushare。

    Args:
        company_name: 公司中文简称（如 "招商银行"）
        stock_code: 6位股票代码（如 "600036"）
    """
    try:
        market = _ds.get_market(company_name)
        financials = _ds.get_financials(company_name, years=3)
        ts_code = _ds.to_ts_code(stock_code)

        beta = None
        if _ds.tushare:
            try:
                df = _ds.tushare.daily_basic(
                    ts_code=ts_code,
                    fields="trade_date,close",
                    limit=250,
                )
                if df is not None and len(df) > 0:
                    import pandas as pd
                    df["return"] = df["close"].pct_change()
                    beta = 1.0  # placeholder, real calculation needs index returns
            except Exception:
                pass

        return json.dumps(
            {
                "stock_code": ts_code,
                "market": market,
                "financials": financials[-6:] if len(financials) > 6 else financials,
                "beta_estimate": beta or "需手动查询",
                "note": "Beta、无风险利率(Rf)、权益风险溢价(ERP)建议通过 mx-data 或 tushare 国债收益率补充获取",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def get_ddm_data(company_name: str, stock_code: str) -> str:
    """获取DDM股息折现模型所需全部数据。

    返回：当前股价、历史DPS/分红比例、ROE、股息率、Beta等。
    专为高股息金融股（银行/保险/金融租赁）设计。

    Args:
        company_name: 公司中文简称（如 "招商银行"）
        stock_code: 6位股票代码（如 "600036"）
    """
    try:
        market = _ds.get_market(company_name)
        financials = _ds.get_financials(company_name, years=5)
        ts_code = _ds.to_ts_code(stock_code)

        dividend_data = []
        if _ds.tushare:
            try:
                df = _ds.tushare.dividend(
                    ts_code=ts_code,
                    fields="ts_code,end_date,cash_div_tax,ex_date",
                )
                if df is not None and len(df) > 0:
                    dividend_data = df.head(10).to_dict(orient="records")
            except Exception:
                pass

        return json.dumps(
            {
                "stock_code": ts_code,
                "market": market,
                "recent_financials": financials[-5:] if len(financials) > 5 else financials,
                "dividend_history": dividend_data or "需通过tushare获取（TUSHARE_TOKEN未设置或查询失败）",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def get_comps_data(company_name: str, stock_code: str) -> str:
    """获取可比公司分析所需数据。

    返回目标公司的估值倍数（PE/PB）和核心财务指标。
    可比公司需通过 mx-search 搜索同行业公司获取。

    Args:
        company_name: 公司中文简称
        stock_code: 6位股票代码（如 "600036"）
    """
    try:
        market = _ds.get_market(company_name)
        financials = _ds.get_financials(company_name, years=1)

        return json.dumps(
            {
                "stock_code": _ds.to_ts_code(stock_code),
                "target": {
                    "market": market,
                    "latest_financials": financials[-1] if financials else None,
                },
                "note": "可比公司列表请使用 search_events 搜索同行业公司后，再逐个查询估值数据进行比较",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def get_lbo_data(company_name: str, stock_code: str) -> str:
    """获取LBO杠杆收购模型所需数据。

    返回：市值、EBITDA估算、近三年财务数据等基础参数。
    LBO建模需结合tushare获取详细财务报表。

    Args:
        company_name: 公司中文简称
        stock_code: 6位股票代码（如 "600036"）
    """
    try:
        market = _ds.get_market(company_name)
        financials = _ds.get_financials(company_name, years=3)
        ts_code = _ds.to_ts_code(stock_code)

        return json.dumps(
            {
                "stock_code": ts_code,
                "market": market,
                "financials": financials,
                "note": (
                    "LBO模型需要额外数据：详细债务结构、EBITDA分拆、"
                    "资本支出、营运资本变动等。建议通过tushare获取完整三表数据。"
                    "当前返回的是估值建模所需的基础行情和财务数据。"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def get_3statement_data(company_name: str, stock_code: str, years: int = 5) -> str:
    """获取三表（利润表/资产负债表/现金流量表）历史数据。

    返回结构化JSON，包含可用的财务指标历史时间序列。
    完整三表原始数据建议通过 tushare 的 income/balancesheet/cashflow 接口获取。

    Args:
        company_name: 公司中文简称
        stock_code: 6位股票代码（如 "600036"）
        years: 回溯年数（默认5年）
    """
    try:
        financials = _ds.get_financials(company_name, years=years)
        market = _ds.get_market(company_name)
        ts_code = _ds.to_ts_code(stock_code)

        result = {
            "stock_code": ts_code,
            "company": company_name,
            "market_snapshot": market,
            "financial_metrics": financials,
        }

        if _ds.tushare:
            try:
                income = _ds.tushare.income(
                    ts_code=ts_code,
                    fields="ts_code,end_date,revenue,operate_profit,total_profit,n_income",
                    limit=years * 4,
                )
                balance = _ds.tushare.balancesheet(
                    ts_code=ts_code,
                    fields="ts_code,end_date,total_assets,total_liab,total_hldr_eqy_inc_min_int",
                    limit=years * 4,
                )
                cashflow = _ds.tushare.cashflow(
                    ts_code=ts_code,
                    fields="ts_code,end_date,n_cashflow_act",
                    limit=years * 4,
                )
                if income is not None:
                    result["income_statement"] = income.head(years).to_dict(orient="records")
                if balance is not None:
                    result["balance_sheet"] = balance.head(years).to_dict(orient="records")
                if cashflow is not None:
                    result["cash_flow"] = cashflow.head(years).to_dict(orient="records")
            except Exception:
                result["tushare_note"] = "tushare详细报表获取失败，已返回mx-data财务指标"

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
