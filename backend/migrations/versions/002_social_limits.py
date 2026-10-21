"""Social evidence, curated places and shared rate limits."""
from alembic import op
import sqlalchemy as sa
revision='002'
down_revision='001'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('rate_buckets',sa.Column('id',sa.String(64),primary_key=True),sa.Column('count',sa.Integer(),nullable=False),sa.Column('expires',sa.Integer(),nullable=False))
    op.create_table('social_videos',sa.Column('id',sa.String(64),primary_key=True),sa.Column('payload',sa.Text(),nullable=False))
    op.create_table('hotspots',sa.Column('id',sa.String(64),primary_key=True),sa.Column('payload',sa.Text(),nullable=False),sa.Column('created_at',sa.String(40),nullable=False))
def downgrade():
    op.drop_table('hotspots');op.drop_table('social_videos');op.drop_table('rate_buckets')
