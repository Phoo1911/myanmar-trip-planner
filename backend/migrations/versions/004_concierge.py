"""Private travel desk and local verification facts."""
from alembic import op
import sqlalchemy as sa
revision='004'
down_revision='003'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('journey_requests',sa.Column('id',sa.String(64),primary_key=True),sa.Column('key',sa.String(64),unique=True,nullable=False),sa.Column('fingerprint',sa.String(64),nullable=False),sa.Column('token_hash',sa.String(64),nullable=False),sa.Column('payload',sa.Text(),nullable=False),sa.Column('status',sa.String(32),nullable=False),sa.Column('version',sa.Integer(),nullable=False))
    op.create_table('local_facts',sa.Column('id',sa.String(64),primary_key=True),sa.Column('place_id',sa.String(64),nullable=False),sa.Column('payload',sa.Text(),nullable=False),sa.Column('version',sa.Integer(),nullable=False))
    op.create_index('ix_local_facts_place_id','local_facts',['place_id'])
def downgrade():
    op.drop_index('ix_local_facts_place_id',table_name='local_facts')
    op.drop_table('local_facts');op.drop_table('journey_requests')
