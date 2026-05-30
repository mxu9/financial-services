"""公共函数：Skill 加载、报告保存、数据提取."""

import json
import os
import re
from datetime import datetime
from urllib.parse import quote
from shared.clients import DataSourceManager
from shared.formatters import now_str, date_to_short

_ds = DataSourceManager()
_REPORT_BASE = os.getenv("REPORT_BASE_URL", "http://127.0.0.1:8000")

_SKILL_DIR = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "plugins", "vertical-plugins", "equity-research", "skills",
)


def _extract_tables(raw: dict) -> list:
    """从 mx-data 原始响应中提取 dataTableDTOList."""
    dto = raw.get("data", {}).get("data", {}).get("searchDataResultDTO", {})
    return dto.get("dataTableDTOList", [])


def _strip_skill_instructions(content: str) -> str:
    """去除 SKILL.md 中不适合作 LLM system prompt 的章节。

    MCP Tool 内部已完成数据收集，LLM 只需生成报告，
    不需要 shell 命令、工作流步骤、数据源配置等执行指令。
    """
    content = re.sub(r"## 数据源配置.*?(?=## |$)", "", content, flags=re.DOTALL)
    content = re.sub(
        r"## 自动化分析工作流.*?(?=## 输出模板格式约束|## 示例|$)",
        "", content, flags=re.DOTALL,
    )
    content = re.sub(r"`cd ~/.*?`", "", content)
    content = re.sub(r"```\ncd ~/.*?```", "", content, flags=re.DOTALL)
    content = re.sub(r".*使用方式：.*", "", content)
    content = re.sub(r".*mx-search（一级.*|.*mx-data（一级.*|.*zhipu-websearch.*", "", content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content


def _load_skill(skill_name: str) -> str:
    """读取 SKILL.md 并去除 YAML frontmatter，作为 LLM system prompt。

    MCP Tool 的分析框架与 Claude Code Skill 共享同一来源（SKILL.md），
    确保两者输出质量和格式保持一致。
    """
    path = os.path.join(_SKILL_DIR, skill_name, "SKILL.md")
    if not os.path.isfile(path):
        return "你是一个资深A股分析师。请基于提供的数据进行分析，输出Markdown报告。"

    with open(path, encoding="utf-8") as f:
        content = f.read()

    if content.startswith("---"):
        parts = content.split("---", 2)
        content = parts[2] if len(parts) > 2 else content

    return _strip_skill_instructions(content).strip()


def _save_report(company: str, content: str) -> str:
    """保存报告到 reports/ 目录，返回文件名."""
    reports_dir = os.path.join(os.getcwd(), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    short_ts = datetime.now().strftime("%y%m%d_%H%M%S")
    filename = f"{company}_事件分析报告_{short_ts}.md"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filename
