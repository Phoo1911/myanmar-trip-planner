"""Allocated inventory and direct reservations."""
from alembic import op
import sqlalchemy as sa
revision='003'
down_revision='002'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('inventory',sa.Column('id',sa.String(64),primary_key=True),sa.Column('payload',sa.Text(),nullable=False),sa.Column('remaining',sa.Integer(),nullable=False),sa.Column('version',sa.Integer(),nullable=False),sa.Column('valid_until',sa.String(40),nullable=False),sa.CheckConstraint('remaining >= 0',name='inventory_nonnegative'))
    op.create_table('reservations',sa.Column('id',sa.String(64),primary_key=True),sa.Column('key',sa.String(64),unique=True,nullable=False),sa.Column('fingerprint',sa.String(64),nullable=False),sa.Column('token_hash',sa.String(64),nullable=False),sa.Column('inventory_id',sa.String(64),nullable=False),sa.Column('guests',sa.Integer(),nullable=False),sa.Column('payload',sa.Text(),nullable=False),sa.Column('status',sa.String(20),nullable=False))
def downgrade():
    op.drop_table('reservations');op.drop_table('inventory')
