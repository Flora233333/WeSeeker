from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ToolSpec:
    name: str
    schema: dict
    handler: Callable[..., str]


@dataclass
class ErrorEvent:
    event_type: str
    user_visible_message: str
    system_message: str
    debug_message: Optional[str] = None
    source: Optional[str] = None


LLM_EMPTY_RESPONSE_EVENT = ErrorEvent(
    event_type="llm_empty_response",
    user_visible_message="我这次没有拿到有效回复。你可以重试一次，或直接补充文件关键词、类型、时间范围。",
    system_message=(
        "上一轮响应异常：你没有返回 tool calls，也没有返回任何文本内容。"
        "本轮必须二选一：若需要调用工具，请返回合法的 tool call；"
        "若不需要调用工具，请直接返回对用户可见的中文回复。"
        "不要再次返回空内容。"
    ),
    debug_message="LLM returned neither tool calls nor content",
    source="Agent._run_reasoning_loop",
)


ERROR_EVENTS = {
    "llm_empty_response": LLM_EMPTY_RESPONSE_EVENT,
}


@dataclass
class PauseEvent:
    reason: str
    system_instruction: str
    default_fallback_msg: str


PAUSE_EVENTS = {
    "empty_search": PauseEvent(
        reason="empty_search",
        system_instruction=(
            "你是文件管家。当前自动工具推理需要暂停，原因：连续多次搜索无结果。"
            "当前关键词可能与实际文件名差异较大，需要用户提供新线索。"
            "用一句轻松的话告诉用户没找到，然后追问一个最可能缩小范围的信息"
            "优先问文件类型（Word/PDF/图片等）或大致存放位置（桌面/下载/文档文件夹）。"
            "语气像朋友随口一问，不要罗列选项，不要连续追问多个维度。"
            "请简短描述现状，进一步询问，以获得用户提示"
        ),
        default_fallback_msg="我连续两次都没找到结果。你可以补充一个关键信息吗：文件类型、时间范围，或大概路径（桌面/下载/文档）？",
    ),
    "duplicate_query": PauseEvent(
        reason="duplicate_query",
        system_instruction=(
            "你是文件管家。当前自动工具推理需要暂停，原因：搜索条件重复，继续调用收益很低。"
            "已有的关键词组合已经穷尽，再搜同样的词没有意义。"
            "直接向用户要一条还没提过的新线索，比如文件后缀名、大概的修改日期或文件大小量级。"
            "如果前几轮已经返回过候选文件列表，优先请用户从中选一个序号确认，而非继续搜索。"
            "语气简洁干脆，像助手提醒'换个方向试试'"
        ),
        default_fallback_msg="同样的搜索条件我已经试过啦。你可以补充一个新的线索吗，比如文件类型或大概修改时间？",
    ),
    "low_gain": PauseEvent(
        reason="low_gain",
        system_instruction=(
            "你是文件管家。当前自动工具推理需要暂停，原因：连续多轮信息增益低。"
            "目前搜索结果趋于重复，继续自动推理效率很低。"
            "给用户两个明确的方向二选一：按文件类型筛选，还是按时间范围筛选。"
            "如果之前已列出候选文件，换一种方式呈现——比如按时间排序后问用户'是最近这几天的吗'。"
            "保持口吻务实，像同事间快速对齐需求，避免客套寒暄。"
        ),
        default_fallback_msg="继续搜索的信息增益很低。你更想按文件类型筛选，还是按时间范围筛选？",
    ),
    "max_steps": PauseEvent(
        reason="max_steps",
        system_instruction=(
            "你是文件管家。当前自动工具推理需要暂停，原因：已达到本轮自动推理上限（5轮）。"
            "先用半句话告知用户本轮自动查找已到上限，再紧接着给出一个具体的补充建议。"
            "建议内容应结合前几轮搜索的盲区——如果之前没试过路径范围就问路径，没试过时间就问时间。"
            "如果已有候选列表，直接请用户挑选或排除，而非要求更多关键词。"
            "语气平和但带有推进感，像是说'咱们换个思路接着来'。"
        ),
        default_fallback_msg="我先停在这里避免无效调用。你可以补充一个更具体线索（文件类型/时间/路径），我再继续精准查找。",
    ),
}

DEFAULT_PAUSE_EVENT = PauseEvent(
    reason="unknown",
    system_instruction=(
        "你是文件管家。当前自动工具推理需要暂停，原因：当前线索不足，无法确定下一步搜索方向。"
        "不要解释技术原因，直接用一句日常口语向用户要一个最关键的补充信息。"
        "可以是文件名中记得的任意片段、文件用途、或者上次打开的大概时间。"
        "只挑一个维度问，别给用户压力。语气轻快自然，像随口搭话，一到两句话结束即可。"
    ),
    default_fallback_msg="为了更快找到目标文件，你可以再补充一个关键信息吗？",
)
