# A股数据源配置规范

本规范定义了 financial-analysis 插件中所有估值模型 skill 的数据源优先级和使用方式。

## 适用范围

以下 skill 应遵循本规范：
- `dcf-model` — DCF 现金流折现模型
- `comps-analysis` — 可比公司分析
- `ddm-model` — DDM 股息折现模型
- `lbo-model` — LBO 杠杆收购模型
- 其他涉及金融数据获取的 skill

---

## ⚠️ 强制前置：时间对齐（任何分析开始前必须执行）

**所有估值分析开始前，必须先打印系统时间并动态计算基准年份：**

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

**A股估值分析必须遵循以下数据源层次：**

1. **mx-data（一级数据源）** — 东方财富妙想 API
   - 行情数据：当前股价、Beta、股息率、总股本、总市值
   - 财务数据：EPS、ROE、每股净资产、毛利率、净利润
   - 使用方式：`cd ~/.claude/skills/mx-data && python mx_data.py "[公司名]" [指标名]`

2. **tushare（补充数据源）** — Tushare Pro API
   - 分红送股明细：历史 DPS、分红方案
   - 财务报表：利润表、资产负债表、现金流量表
   - 债券数据：国债收益率曲线
   - 使用方式：`import tushare as ts; pro = ts.pro_api()`

3. **mx-search（研究数据源）** — 东方财富妙想搜索
   - 分红政策公告、管理层指引
   - 行业研报、券商观点
   - 宏观经济信息（如国债收益率市场解读）
   - 使用方式：`cd ~/.claude/skills/mx-search && python mx_search.py "[搜索内容]"`

4. **zhipu-websearch（后备搜索）** — 智谱 Web Search
   - 使用场景：mx-search 调用失败、API限额耗尽、需要非金融领域信息
   - 认证：环境变量 `ZHIPU_API_KEY`
   - 使用方式：`from zai import ZhipuAiClient`
   - 数据类型：通用网页内容（标题、链接、摘要、发布日期）
   - 建议参数：
     - `search_recency_filter='oneMonth'` — 获取近期信息
     - `search_domain_filter` — 指定权威域名（如 `eastmoney.com`）
   - 注意事项：返回内容为通用网页摘要，需验证数据权威性

## 后备搜索机制

**触发优先级：**
1. 先尝试 mx-search（金融专用，数据权威）
2. 若 mx-search 失败（API错误/限额耗尽/空结果），使用 zhipu-websearch
3. zhipu-websearch 结果需人工确认来源可靠性

**适用场景区分：**
| 搜索需求 | 优先使用 | 后备选择 |
|----------|----------|----------|
| 分红政策公告 | mx-search | zhipu-websearch + 域名过滤 |
| 研报/券商观点 | mx-search | zhipu-websearch（需验证） |
| 非金融信息 | zhipu-websearch | - |

## 股票代码格式

**A股代码格式：**
- 上海证券交易所：`[代码].SH`（如 `600901.SH`）
- 深圳证券交易所：`[代码].SZ`（如 `000001.SZ`）
- 北京证券交易所：`[代码].BJ`

**示例：**
```
江苏金租: 600901.SH
平安银行: 000001.SZ
宁德时代: 300750.SZ
```

## CAPM 参数适配（中国市场）

**无风险利率 (Rf)：**
- 使用中国10年期国债收益率（约 1.5-2.5%，2024-2026年区间）
- 来源：tushare 国债收益率曲线或 mx-search 搜索最新数据

**Beta：**
- 使用沪深300指数作为市场基准
- 5年月度 Beta
- 来源：mx-data

**权益风险溢价 (ERP)：**
- 中国市场 ERP：5.5-7.5%（新兴市场溢价）
- 高于成熟市场的 5-6% 标准

**典型要求回报率 r 范围：**
| 行业 | 典型 r 范围 | 典型 Beta |
|------|------------|----------|
| 大型国有银行 | 7-9% | 0.5-0.8 |
| 股份制/城商行 | 9-11% | 0.7-1.0 |
| 保险 | 9-12% | 0.8-1.2 |
| 金融租赁 | 9-13% | 0.8-1.1 |
| 券商 | 10-13% | 1.0-1.3 |
| 科技成长股 | 12-15% | 1.2-1.5 |

## 永续增长率适配

**中国市场约束：**
- 永续增长率 g 不得高于中国名义 GDP 增长率（约 5-7%）
- 终值增长率通常：2-4%（与长期通胀/GDP增速对齐）
- 高 ROE 公司 5年后 g 向行业均值回归（3-4%）

## 数据时效性要求（强制）

**所有估值模型必须使用最新交易日/报告期数据。**

### 数据时效性检查清单

在开始任何估值分析前，必须验证：

| 数据类型 | 时效性要求 | 验证方法 |
|----------|------------|----------|
| 股价 | 最新交易日（T或T-1） | `trade_date >= 今天-3天` |
| 财务报表 | 最近年报/季报 | `end_date` 为最近报告期 |
| 国债收益率 | 最新交易日 | `trade_date` 为当天或前一交易日 |
| Beta | 最近5年数据 | 包含最近月度数据 |
| 分红数据 | 最近年度分红方案 | `end_date` 为最近年报期 |

### tushare 获取最新数据正确方法

**错误做法（可能返回过期数据）**：
```python
# 错误：不指定日期范围，可能返回历史数据
df = pro.daily(ts_code='600036.SH')
```

**正确做法（强制获取最新数据）**：
```python
import tushare as ts
from datetime import datetime, timedelta

pro = ts.pro_api()
today = datetime.now().strftime('%Y%m%d')
week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

# 获取最新交易日股价
df = pro.daily(ts_code='600036.SH', start_date=week_ago, end_date=today)
latest_price = df.iloc[0]['close']  # 第一行是最新日期
latest_date = df.iloc[0]['trade_date']
print(f'最新股价: ¥{latest_price} ({latest_date})')

# 获取最近年报财务指标
df_fina = pro.fina_indicator(ts_code='600036.SH', period_type='1')
latest_annual = df_fina[df_fina['end_date'].str.endswith('1231')].iloc[0]
print(f'最近年报EPS: {latest_annual["eps"]} ({latest_annual["end_date"]})')
```

### mx-data 时效性说明

mx-data 返回的数据为实时/最新数据：
- 股价：实时行情或最近收盘价
- Beta：最近5年计算结果
- 财务指标：最近报告期数据

### 数据时效性验证脚本

在数据获取后，必须运行验证：
```python
# 验证股价时效性
from datetime import datetime, timedelta
latest_trade_date = df.iloc[0]['trade_date']
date_obj = datetime.strptime(latest_trade_date, '%Y%m%d')
days_old = (datetime.now() - date_obj).days

if days_old > 3:
    print(f'警告: 股价数据已过期 {days_old} 天，请检查数据源')
else:
    print(f'验证通过: 数据日期 {latest_trade_date}')
```

### 数据时效性警告

若数据过期超过以下阈值，必须重新获取或向用户说明：

| 数据类型 | 过期阈值 | 处理方式 |
|----------|----------|----------|
| 股价 | > 3天 | 重新获取，注明数据日期 |
| 财务报表 | > 1季度 | 使用最新可用数据，说明报告期 |
| 国债收益率 | > 7天 | 重新搜索最新数据 |
| 分红方案 | > 1年 | 说明使用历史数据 |

## 数据获取脚本模板

```bash
# 1. 行情 + Beta + 股本（mx-data）
cd ~/.claude/skills/mx-data && python mx_data.py "[公司名]" 最新价 总股本 beta 股息率

# 2. 历史 EPS + ROE（mx-data）
cd ~/.claude/skills/mx-data && python mx_data.py "[公司名]" 近五年 每股收益 净资产收益率

# 3. 历史分红 DPS（tushare）
python -c "
import tushare as ts
pro = ts.pro_api()
df = pro.dividend(ts_code='[代码.SH/SZ]', fields='ts_code,end_date,stk_div,cash_div_tax,ex_date')
print(df.head(20))
"

# 4. 10年期国债收益率（mx-search，因 tushare 接口不稳定）
cd ~/.claude/skills/mx-search && python mx_search.py "中国10年期国债收益率 最新"

# 5. 分红政策公告（mx-search）
cd ~/.claude/skills/mx-search && python mx_search.py "[公司名] 分红政策 利润分配方案"

# 6. 行业数据（mx-data）
cd ~/.claude/skills/mx-data && python mx_data.py "[行业名] 行业 平均股息率"
```

## 认证配置

**mx-data / mx-search：**
- 环境变量：`MX_APIKEY`
- 获取方式：东方财富妙想 Skills 页面（https://dl.dfcfs.com/m/itc4）

**zhipu-websearch：**
- 环境变量：`ZHIPU_API_KEY`
- 获取方式：智谱AI开放平台（https://open.bigmodel.cn/）

**tushare：**
- 环境变量：`TUSHARE_TOKEN`（可选，也可在代码中设置）
- 获取方式：Tushare Pro 注册页面

## 不使用的数据源

以下第三方 MCP 服务在本插件中**不适用**（面向国际市场）：
- Daloopa、FactSet、S&P Global、Morningstar、Moody's、Aiera、LSEG、PitchBook、Chronograph

A股估值应仅使用 mx-data/tushare/mx-search。