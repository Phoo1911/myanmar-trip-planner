"""Initial booking and audit tables."""
from alembic import op
import sqlalchemy as sa
revision='001'
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('bookings',sa.Column('id',sa.String(64),primary_key=True),sa.Column('key',sa.String(64),unique=True,nullable=False),sa.Column('fingerprint',sa.String(64),nullable=False),sa.Column('token_hash',sa.String(64),nullable=False),sa.Column('payload',sa.Text(),nullable=False),sa.Column('status',sa.String(24),nullable=False),sa.Column('version',sa.Integer(),nullable=False),sa.Column('created_at',sa.String(40),nullable=False))
    op.create_table('audit',sa.Column('id',sa.String(64),primary_key=True),sa.Column('booking_id',sa.String(64),nullable=False),sa.Column('action',sa.String(24),nullable=False),sa.Column('created_at',sa.String(40),nullable=False))
def downgrade():
    op.drop_table('audit');op.drop_table('bookings')
