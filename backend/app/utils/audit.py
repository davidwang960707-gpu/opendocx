"""审计日志写入 helper (P1-W3-A1)

供 7 个 PATCH 端点 (project/doc/version/feedback/user) 调:
    await write_audit(db, actor=user, action='project.delete', target_type='project', target_id=pid, payload={...})

设计: **独立 session 写入**, 不依赖调用方 db 的事务状态
(端点 commit/rollback 后 hook 仍能可靠写)
"""
import logging
from typing import Optional, Any
from app.models.audit import AuditLog
from app.models.user import User
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def write_audit(
    actor: Optional[User] = None,
    action: str = "",
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
    actor_email: Optional[str] = None,
) -> None:
    """写一条审计日志, 失败不阻塞主流程 (log warning)

    actor 可为 None (公开 feedback.create 走游客时), 此时 actor_email 必填
    """
    try:
        async with AsyncSessionLocal() as session:
            log = AuditLog(
                actor_id=actor.id if actor else None,
                actor_email=(actor.email if actor else None) or actor_email or "anonymous",
                action=action,
                target_type=target_type,
                target_id=target_id,
                payload=payload,
            )
            session.add(log)
            await session.commit()
    except Exception as e:
        logger.warning(f"[audit] 写日志失败: action={action} target={target_type}/{target_id} err={type(e).__name__}: {e}")
        # 不抛, 让主流程继续
