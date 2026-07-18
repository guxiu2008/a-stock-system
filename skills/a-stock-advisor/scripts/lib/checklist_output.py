#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checklist 通用输出引擎 - 不关心业务逻辑，只负责格式化和输出
输入参数：检查项容器、输出路径、文件名
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


class ChecklistItem:
    """单个检查项"""
    def __init__(self, 
                 title: str,
                 passed: Optional[bool] = None,  # True=✅, False=❌, None=⚠️待验证
                 value: Any = None,
                 unit: str = "",
                 desc: str = ""):
        self.title = title
        self.passed = passed
        self.value = value
        self.unit = unit
        self.desc = desc
    
    def to_markdown(self) -> str:
        """格式化输出为 markdown 的勾选项"""
        status_mark = {
            True:  "✅",
            False: "❌",
            None:  "⚠️"
        }[self.passed]
        
        check_mark = "[x]" if self.passed else "[ ]"
        
        if self.value is not None:
            if isinstance(self.value, float):
                if 0 < self.value < 1000:
                    val_str = f"{self.value:.2f}{self.unit}"
                else:
                    val_str = f"{self.value:.0f}{self.unit}"
            else:
                val_str = f"{self.value}{self.unit}"
            
            # 特殊处理：仅展示分值的项，不显示检查标记
            if self.passed is None and "分" in self.unit:
                return f"- {check_mark} {self.title} → {val_str}"
            else:
                return f"- {check_mark} {self.title} → {val_str} {status_mark}"
        else:
            return f"- {check_mark} {self.title} {status_mark}"


class ChecklistSection:
    """一个章节：包含标题和多个检查项"""
    def __init__(self, title: str, level: int = 2):
        self.title = title
        self.level = level
        self.items: List[ChecklistItem] = []
    
    def add(self, item: ChecklistItem):
        self.items.append(item)
    
    def to_markdown(self) -> List[str]:
        lines = []
        prefix = "#" * self.level
        lines.append(f"{prefix} {self.title}")
        lines.append("")
        for item in self.items:
            lines.append(item.to_markdown())
        return lines


class ChecklistContainer:
    """Checklist 容器 - 承载所有检查结果"""
    def __init__(self, stock_code: str, stock_name: str, checklist_type: str):
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.checklist_type = checklist_type  # short/swing/growth
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.sections: List[ChecklistSection] = []
        self.meta: Dict[str, Any] = {}
    
    def add_section(self, section: ChecklistSection):
        self.sections.append(section)
    
    def set_meta(self, key: str, value: Any):
        self.meta[key] = value


class ChecklistOutput:
    """Checklist 输出引擎"""
    
    @staticmethod
    def to_markdown(container: ChecklistContainer) -> str:
        """将容器内容转换为 markdown 格式"""
        lines = []
        
        # 标题
        type_names = {
            "short": "短线策略清单",
            "swing": "单股评估清单",
            "growth": "中线策略清单",
        }
        type_name = type_names.get(container.checklist_type, "评估清单")
        lines.append(f"# {type_name} - {container.stock_name}({container.stock_code})")
        lines.append("")
        
        # 元信息
        meta_lines = [f"> 评估日期：{container.date}"]
        if "close" in container.meta:
            meta_lines.append(f" 收盘价：{container.meta['close']:.2f}")
        if "industry" in container.meta:
            meta_lines.append(f" 行业：{container.meta['industry']}")
        lines.append(" ".join(meta_lines))
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 各个章节
        for section in container.sections:
            lines.extend(section.to_markdown())
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # 免责声明
        lines.append("> [免责声明] 本清单仅供参考，不构成投资建议。请严格执行你的交易纪律。")
        
        return "\n".join(lines)
    
    @staticmethod
    def save_to_file(container: ChecklistContainer, 
                    output_dir: str = None,
                    filename: str = None) -> str:
        """保存到文件
        
        Args:
            container: Checklist 容器
            output_dir: 输出目录（支持日期子文件夹，如 {date}）
            filename: 文件名，支持变量 {code}, {type}, {ts}
        """
        if output_dir is None:
            output_dir = os.environ.get("CHECKLIST_OUTPUT_DIR", "./output")
        
        # 支持日期子文件夹
        date_str = datetime.now().strftime("%Y%m%d")
        output_dir = output_dir.replace("{date}", date_str)
        
        # 生成默认文件名
        if filename is None:
            ts = datetime.now().strftime("%H%M%S")
            filename = f"{container.stock_code}_{container.checklist_type}_{ts}.md"
        
        # 变量替换
        filename = filename.replace("{code}", container.stock_code)
        filename = filename.replace("{type}", container.checklist_type)
        filename = filename.replace("{ts}", datetime.now().strftime("%H%M%S"))
        
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        # 写入文件
        markdown = ChecklistOutput.to_markdown(container)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        return filepath
