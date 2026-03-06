from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ReasoningState:
    step_count: int = 0
    empty_search_streak: int = 0
    low_gain_streak: int = 0
    duplicate_query_hits: int = 0

    def apply_step_signals(self, step_signals: List[str], has_candidates: bool) -> None:
        if "search_empty" in step_signals and not has_candidates:
            self.empty_search_streak += 1
        elif "search_has_candidates" in step_signals:
            self.empty_search_streak = 0

        if "duplicate_query" in step_signals:
            self.duplicate_query_hits += 1

        gain_signals = {"search_has_candidates", "preview_success", "send_done"}
        if any(signal in gain_signals for signal in step_signals):
            self.low_gain_streak = 0
        else:
            self.low_gain_streak += 1

    def should_stop(
        self,
        max_empty_search_streak: int,
        max_low_gain_streak: int,
        has_candidates: bool,
    ) -> Optional[str]:
        if self.empty_search_streak >= max_empty_search_streak and not has_candidates:
            return "empty_search"

        if self.duplicate_query_hits >= 1 and self.step_count >= 2 and not has_candidates:
            return "duplicate_query"

        if self.low_gain_streak >= max_low_gain_streak and not has_candidates:
            return "low_gain"

        return None
