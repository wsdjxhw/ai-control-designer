"""演化日志记录器。

将每轮演化的参数、代价、诊断报告记录到 JSON 文件，
并提供分层历史注入接口供 LLM 诊断使用。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any


class EvolutionLogger:
    """演化日志记录器，支持 JSON 持久化和分层历史查询。"""

    def __init__(self, log_file: str, work_dir: str = "") -> None:
        self.log_file = log_file
        self.work_dir = work_dir
        self._records: list[dict[str, Any]] = []
        self._load_existing()

    def _load_existing(self) -> None:
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    self._records = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._records = []

    def log_iteration(
        self,
        version: int,
        params: dict[str, float],
        cost: float,
        diagnosis: str = "",
        metrics: dict | None = None,
        param_count: int = 0,
    ) -> None:
        """记录一轮演化迭代。"""
        record = {
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "params": params,
            "cost": cost,
            "param_count": param_count,
            "diagnosis_summary": (
                diagnosis[:500] if len(diagnosis) > 500 else diagnosis
            ),
            "diagnosis": diagnosis,  # 🆕 完整报告
            "metrics": metrics or {},
        }
        self._records.append(record)
        self._flush()

    def _flush(self) -> None:
        dir_name = os.path.dirname(self.log_file)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(self._records, f, ensure_ascii=False, indent=2)

    def get_layered_history(self, n_recent_full: int = 3) -> str:
        """生成分层历史文本供 LLM 诊断使用。

        包含：
        - 完整列表（所有演化版本摘要）
        - 失败模式总结
        - 早期洞察（前三轮）
        - 最近 n_recent_full 轮的完整记录
        """
        parts: list[str] = []

        # 1. 完整列表
        lines = ["=== 演化历史 (完整) ==="]
        for r in self._records:
            lines.append(
                f"  V{r['version']}: cost={r['cost']:.4f}, "
                f"params={r['param_count']}个"
            )
        parts.append("\n".join(lines))

        # 2. 失败模式
        if self._records:
            costs = [r["cost"] for r in self._records]
            min_cost = min(costs)
            max_cost = max(costs)
            parts.append(
                f"=== 失败模式 ===\n"
                f"  最优代价: {min_cost:.4f}, 最差代价: {max_cost:.4f}, "
                f"  迭代次数: {len(self._records)}"
            )

        # 3. 早期洞察（前 3 轮）
        early = self._records[:3]
        if early:
            early_lines = ["=== 早期洞察 (前3轮) ==="]
            for r in early:
                early_lines.append(
                    f"  V{r['version']}: cost={r['cost']:.4f}, "
                    f"params={r['params']}"
                )
            parts.append("\n".join(early_lines))

        # 4. 最近几轮的完整记录
        recent = self._records[-n_recent_full:] if n_recent_full > 0 else []
        if recent:
            recent_lines = [f"=== 最近 {len(recent)} 轮完整记录 ==="]
            for r in recent:
                recent_lines.append(
                    f"--- V{r['version']} ---\n"
                    f"  cost={r['cost']:.4f}\n"
                    f"  params={r['params']}\n"
                    f"  诊断摘要: {r.get('diagnosis_summary', '')[:300]}"
                )
            parts.append("\n".join(recent_lines))

        return "\n\n".join(parts)

    @property
    def records(self) -> list[dict[str, Any]]:
        return self._records

    def clear(self) -> None:
        self._records = []
        self._flush()
