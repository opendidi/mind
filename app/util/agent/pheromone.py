# -*- coding: UTF-8 -*-
"""AgentPheromone — 共享上下文黑板（蚁群信息素模式）

DAG 节点间的"信息素"共享层：
- 每步工具执行成功后，自动提取关键发现
- 后续节点的 ReAct 提示词自动注入已发现的信息
- 避免每个节点重复探索相同的上下文
"""

import time
from collections import OrderedDict

# 需要从工具结果中自动提取的关键字段（mind 项目通用）
_EXTRACTABLE_KEYS = {
    "pen_id",
    "blueprint_id",
    "file_id",
    "name",
    "type",
    "text",
}

# 工具名 → 结果中值得提取的子字段
_TOOL_RESULT_PATHS = {
    "canvas": ["data"],
    "blueprint_list": ["data"],
    "blueprint_search": ["data"],
    "file_search": ["data"],
}


class SharedContext:
    """跨 DAG 节点的共享信息黑板。

    每个节点执行前从黑板"嗅探"已知信息；
    每个工具执行成功后向黑板"沉积"新发现。
    """

    def __init__(self, max_entries: int = 20):
        self._facts: OrderedDict = OrderedDict()
        self._max = max_entries

    def deposit(self, key: str, value, source_node: str = "", source_tool: str = ""):
        """存入一条发现。若 key 已存在则跳过（先到先得）。"""
        import logging

        if key in self._facts:
            return
        if len(self._facts) >= self._max:
            evicted_key = next(iter(self._facts))
            self._facts.popitem(last=False)
            logging.debug("Pheromone evicted: %s (from %s)", evicted_key, source_node)
        self._facts[key] = {
            "value": value,
            "source_node": source_node,
            "source_tool": source_tool,
            "ts": time.time(),
        }

    _SNIFF_MAX_LEN = 1200

    def sniff(self) -> str:
        """嗅探所有已知信息，返回可注入 LLM 提示词的格式化文本。"""
        if not self._facts:
            return ""
        import re

        lines = ["## 已知信息（前面步骤已发现，可直接使用，无需重复查询）"]
        total = 0
        for key, entry in self._facts.items():
            raw = str(entry["value"])
            clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw)[:300]
            line = f"- {key}: {clean}"
            total += len(line)
            if total > self._SNIFF_MAX_LEN:
                lines.append(f"...(截断，共{len(self._facts)}条发现)")
                break
            lines.append(line)
        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {k: v["value"] for k, v in self._facts.items()}

    def __len__(self):
        return len(self._facts)

    def __repr__(self):
        return f"SharedContext({len(self._facts)} facts)"


def extract_discoveries(tool_name: str, tool_args: dict, result: dict) -> dict[str, object]:
    """从工具执行结果中自动提取关键发现。"""
    discoveries = {}
    if not result.get("success"):
        return discoveries

    # 1. 从调用参数中提取 ID 类字段
    for key in ("pen_id", "blueprint_id", "file_id"):
        if key in tool_args and tool_args[key]:
            discoveries[key] = tool_args[key]

    # 2. 从工具结果中提取
    paths = _TOOL_RESULT_PATHS.get(tool_name, [])
    for path in paths:
        container = result
        if path:
            container = result.get(path)
        if container is None:
            continue
        if isinstance(container, dict):
            _extract_from_dict(container, discoveries)
        elif isinstance(container, list):
            for item in container:
                if isinstance(item, dict):
                    _extract_from_dict(item, discoveries)

    # 3. 特殊处理顶层字段
    for key in _EXTRACTABLE_KEYS:
        if key in result and key not in discoveries:
            val = result[key]
            if val is not None and val != "":
                discoveries[key] = val

    return discoveries


def _extract_from_dict(data: dict, bucket: dict):
    """从单个 dict 中提取可识别字段。"""
    id_keys = ["id", "pen_id", "blueprint_id", "file_id", "name"]
    for key in id_keys:
        if key in data and data[key] is not None and data[key] != "":
            bucket[key] = data[key]
    desc_keys = ["name", "title", "type", "text"]
    for key in desc_keys:
        if key in data and data[key] is not None and data[key] != "" and key not in bucket:
            bucket[key] = data[key]
