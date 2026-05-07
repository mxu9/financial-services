# A股数据源配置规范

本规范定义了 financial-analysis 插件中所有估值模型 skill 的数据源优先级和使用方式。

## 适用范围

以下 skill 应遵循本规范：
- `dcf-model` — DCF 现金流折现模型
- `comps-analysis` — 可比公司分析
- `ddm-model` — DDM 股息折现模型
- `lbo-model` — LBO 杠杆收购模型
- 其他涉及金融数据获取的 skill

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

**tushare：**
- 环境变量：`TUSHARE_TOKEN`（可选，也可在代码中设置）
- 获取方式：Tushare Pro 注册页面

## 不使用的数据源

以下第三方 MCP 服务在本插件中**不适用**（面向国际市场）：
- Daloopa、FactSet、S&P Global、Morningstar、Moody's、Aiera、LSEG、PitchBook、Chronograph

A股估值应仅使用 mx-data/tushare/mx-search。