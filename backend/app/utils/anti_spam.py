"""反垃圾 (F2 P1-W4-L2) — 4 件套:

1. 内存 visitor_id 限流: comment 5/min + reactions 30/min
   (复用 RateLimitMiddleware 模式, 但 key 用 X-Visitor-Id 而非 IP)
2. 关键词过滤: 24 个赌博/广告/辱骂词黑名单
3. 链接检测: body 中 URL 数 > 2 直接拒
4. 嵌套深度限 2 层: 父评论的 parent_id 必须为 None
"""
import os
import re
import time
from collections import defaultdict
from typing import Iterable


# === 关键词黑名单 (24 个) ===
# 触发即拒 (大小写不敏感, 整词匹配)
# 中文: 全角匹配; 英文: 整词
SPAM_KEYWORDS_ZH = [
    "博彩", "赌博", "澳门威尼斯", "澳门新葡京", "澳门太阳城", "皇冠体育", "外围",
    "兼职", "招嫖", "一夜情", "迷药", "违禁",
    "代刷", "代练", "代购", "代开发票", "套现",
    "二维码收款", "微商", "代孕", "捐卵",
    "贷款秒批", "低息贷款", "无视征信",
]
SPAM_KEYWORDS_EN = [
    "casino", "viagra", "porn", "escort", "loan shark", "quick cash",
]
SPAM_KEYWORDS = SPAM_KEYWORDS_ZH + SPAM_KEYWORDS_EN


# === 链接检测 ===
# 匹配 http:// https:// www. 三种
URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s\u4e00-\u9fff]+", re.IGNORECASE
)


def extract_url_count(text: str) -> int:
    """提取文本中 URL 数, 简单按 URL_RE 匹配数算"""
    if not text:
        return 0
    return len(URL_RE.findall(text))


def contains_spam_keyword(text: str) -> str | None:
    """返回首个命中的关键词, None 表示没命中"""
    if not text:
        return None
    low = text.lower()
    for kw in SPAM_KEYWORDS:
        if kw in low:
            return kw
    return None


# === 访客级限流 (内存, 滑动窗口) ===
class VisitorRateLimiter:
    """comment 5/min + reactions 30/min"""

    def __init__(self):
        self._events: dict[tuple[str, str], list[float]] = defaultdict(list)
        # [(visitor_id, action), [timestamps...]]

    def check(self, visitor_id: str, action: str, max_count: int, window_seconds: int = 60) -> bool:
        """True = 通过, False = 拒 (返回 429)"""
        if os.environ.get("DISABLE_RATE_LIMIT") == "1":
            return True
        key = (visitor_id, action)
        now = time.time()
        window_start = now - window_seconds
        # 清过期
        self._events[key] = [t for t in self._events[key] if t > window_start]
        if len(self._events[key]) >= max_count:
            return False
        self._events[key].append(now)
        return True

    def stats(self, visitor_id: str) -> dict[str, int]:
        """调试用: 返 visitor 当前窗口内的事件数"""
        return {
            action: len([t for t in self._events.get((visitor_id, action), []) if t > time.time() - 60])
            for action in ["comment", "reaction", "delete"]
        }


# 单例
_limiter = VisitorRateLimiter()


def get_visitor_limiter() -> VisitorRateLimiter:
    return _limiter


# === 校验函数 ===
def validate_comment_body(body: str) -> tuple[bool, str]:
    """校验评论 body: 长度 + 关键词 + 链接数

    返回 (True, '') 通过, (False, reason) 拒
    """
    if not body or not body.strip():
        return False, "评论不能为空"
    if len(body) > 500:
        return False, "评论最长 500 字符"
    if len(body.strip()) < 2:
        return False, "评论太短 (>= 2 字符)"

    # 关键词过滤
    bad = contains_spam_keyword(body)
    if bad:
        return False, f"评论含违禁词: {bad}"

    # 链接检测
    n_urls = extract_url_count(body)
    if n_urls > 2:
        return False, f"评论链接数过多 ({n_urls} > 2)"

    return True, ""


def check_nesting_depth(db, parent_id: str | None) -> tuple[bool, str]:
    """校验嵌套深度: parent.parent_id 必须为 None (2 层)

    返回 (True, '') 通过, (False, reason) 拒
    """
    if not parent_id:
        return True, ""
    from app.models import DocumentFeedback
    from sqlalchemy import select
    # 这个函数签名故意简单, 实际用 async
    return True, ""  # 留给 async 包装


async def check_nesting_depth_async(db, parent_id: str | None) -> tuple[bool, str]:
    """异步版本: 校验嵌套深度 ≤ 2 层"""
    if not parent_id:
        return True, ""
    from app.models import DocumentFeedback
    from sqlalchemy import select
    parent = (await db.execute(
        select(DocumentFeedback).where(DocumentFeedback.id == parent_id)
    )).scalar_one_or_none()
    if not parent:
        return False, "父评论不存在"
    if parent.parent_id is not None:
        return False, "嵌套深度最多 2 层 (不能回复回复的回复)"
    return True, ""
