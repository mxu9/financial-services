# A股数据源配置规范（equity-research）

本规范定义了 equity-research 插件中所有研究分析 skill 的数据源优先级和使用方式。

## 适用范围

- `stock-assessment` — A股系统性估值分析
- `stock-event-analysis` — 上市公司事件影响分析
- `earnings-analysis` — 季度财报分析
- `initiating-coverage` — 首次覆盖研究报告
- `sector-overview` — 行业板块概览
- `catalyst-calendar` — 催化剂事件日历
- `earnings-preview` — 业绩前瞻分析
- `morning-note` — 晨会纪要
- `thesis-tracker` — 投资主题跟踪

---

## ⚠️ 强制前置：时间对齐（任何分析开始前必须执行）

**所有分析开始前，必须先打印系统时间并动态计算基准年份：**

```python
from datetime import datetime
now = datetime.now()
print(f"SYSTEM_TIME: {now.strftime('%Y-%m-%d')}")

base_year = now.year - 1      # 基准年度（年报分析基准，如2026年分析则base_year=2025）
latest_year = now.year        # 边际年度（最新财报期可能年份）
```

**年份动态衍生规则：**

| 年份变量 | 定义 | 用途 |
|----------|------|------|
| `base_year` | `now.year - 1` | 基准年报年度（如分析基于2025年报） |
| `latest_year` | `now.year` | 最新财报期可能的年份（含当年季报） |
| `historical_years` | `[base_year-4, base_year-3, base_year-2, base_year-1]` | 5年历史数据范围 |

**示例（假设当前时间为 2026-05-07）：**
```
SYSTEM_TIME: 2026-05-07
base_year = 2025    # 分析基准：2025年年报
latest_year = 2026  # 最新数据：2026年一季度
historical_years = [2021, 2022, 2023, 2024, 2025]  # 5年历史
```

---

## 🚫 严格禁止：幻觉和假设

**禁止幻觉**：严禁硬编码年份，所有年份必须由系统时间动态衍生。

```python
# ❌ 错误：硬编码年份（幻觉）
eps_2024 = 5.66  # 如果现在是2026年，这是过期假设
historical_data = [2020, 2021, 2022, 2023, 2024]  # 固定年份列表

# ✅ 正确：动态衍生年份
now = datetime.now()
base_year = now.year - 1
historical_years = [base_year - i for i in range(5, 0, -1)]
```

**禁止假设**：绝对不得使用"假设值"或"行业平均值"替代真实财报数据。

```python
# ❌ 错误：使用假设值
beta = 0.8  # "假设股份制银行Beta为0.8" → 禁止
roe = 0.12  # "行业平均ROE" → 禁止，必须获取公司实际数据

# ✅ 正确：获取真实数据
df = pro.fina_indicator(ts_code='600036.SH', period_type='1')
actual_roe = df[df['end_date'].str.endswith(f'{base_year}1231')]['roe'].iloc[0]
print(f'实际ROE ({base_year}年报): {actual_roe:.2%}')
```

**数据缺失时的正确处理：**

若真实数据无法获取，必须：
1. 明确向用户说明："数据源无法获取 [指标名]，请提供该数据或选择替代方案"
2. 等待用户决策，不得擅自使用假设值填充
3. 若用户同意使用替代值，必须注释说明来源："用户提供的估计值"

---

## 数据源优先级

1. **mx-data（一级数据源）** — 东方财富妙想 API
   - 行情数据：当前股价、Beta、股息率、总股本、总市值
   - 财务数据：EPS、ROE、每股净资产、毛利率、净利润
   - 股东与解禁：大股东质押比例、限售股解禁日历
   - 使用方式：`python mx_data.py "[公司名]" [指标名]`

2. **mx-search（一级数据源）** — 东方财富妙想搜索
   - 公司公告、行业政策、券商研报
   - 机构盈利预测、评级变化
   - 宏观经济数据解读（国债收益率、M2、工业增加值）
   - 使用方式：`python mx_search.py "[搜索内容]"`

3. **tushare（补充数据源）** — Tushare Pro API
   - 分红送股明细：历史 DPS、分红方案
   - 财务报表：利润表、资产负债表、现金流量表
   - 债券数据：国债收益率曲线、AAA 企业债收益率
   - 使用方式：`import tushare as ts; pro = ts.pro_api()`

4. **zhipu-websearch（后备搜索）** — 智谱 Web Search
   - mx-search 失败或 API 限额耗尽时使用
   - 适用场景：社融数据、万得全 A 成交额、行业政策查询等

---

## 股票代码格式

- 上海证券交易所：`[代码].SH`（如 `600036.SH`）
- 深圳证券交易所：`[代码].SZ`（如 `000001.SZ`）
- 北京证券交易所：`[代码].BJ`

---

## 不使用的数据源

以下第三方 MCP 服务在本插件中**不适用**（面向国际市场）：
- Daloopa、FactSet、S&P Global、Morningstar、Moody's、Aiera、LSEG、PitchBook、Chronograph

A股分析应仅使用 mx-data / mx-search / tushare / zhipu-websearch。
