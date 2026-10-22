"""Unlisted trip share links."""
from alembic import op
import sqlalchemy as sa
revision='005'
down_revision='004'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('shared_trips',sa.Column('id',sa.String(32),primary_key=True),sa.Column('payload',sa.Text(),nullable=False),sa.Column('expires',sa.Integer(),nullable=False))
    op.create_index('ix_shared_trips_expires','shared_trips',['expires'])
def downgrade():
    op.drop_index('ix_shared_trips_expires',table_name='shared_trips')
    op.drop_table('shared_trips')
