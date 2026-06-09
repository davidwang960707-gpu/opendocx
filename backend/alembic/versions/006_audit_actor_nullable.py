"""audit_logs.actor_id 改 nullable (公开 feedback 操作)

P1-W3-A1-7: feedback.create/delete 走公开访客, actor_id=None, 必须 nullable
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "audit_logs",
        "actor_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )


def downgrade() -> None:
    # 反向: 先把所有 NULL 改成 'system' 占位 (不能真删)
    op.execute("UPDATE audit_logs SET actor_id = 'system' WHERE actor_id IS NULL")
    op.alter_column(
        "audit_logs",
        "actor_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
