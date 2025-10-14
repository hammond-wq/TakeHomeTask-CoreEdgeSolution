from alembic import op
import sqlalchemy as sa

revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'agent',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('language', sa.String(length=40), nullable=False, server_default='English'),
        sa.Column('voice_type', sa.String(length=40), nullable=False, server_default='Male'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index('ix_agent_name', 'agent', ['name'])

    op.create_table(
        'driver',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('phone_number', sa.String(length=32), nullable=False, unique=True),
    )
    op.create_index('ix_driver_phone', 'driver', ['phone_number'], unique=True)

    op.create_table(
        'calllog',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('agent_id', sa.Integer(), sa.ForeignKey('agent.id'), nullable=False),
        sa.Column('driver_id', sa.Integer(), sa.ForeignKey('driver.id'), nullable=True),
        sa.Column('load_number', sa.String(length=64), nullable=False),
        sa.Column('call_start_time', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('call_end_time', sa.DateTime(), nullable=True),
        sa.Column('call_outcome', sa.String(length=40), nullable=False, server_default='queued'),
        sa.Column('provider_call_id', sa.String(length=128), nullable=True),
        sa.Column('structured_payload', sa.JSON(), nullable=True),
    )
    op.create_index('ix_calllog_load', 'calllog', ['load_number'])
    op.create_index('ix_calllog_start', 'calllog', ['call_start_time'])
    op.create_index('ix_calllog_outcome', 'calllog', ['call_outcome'])
    op.create_index('ix_calllog_provider', 'calllog', ['provider_call_id'])
    op.create_index('ix_calllog_outcome_start', 'calllog', ['call_outcome', 'call_start_time'])

    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('call_log_id', sa.Integer(), sa.ForeignKey('calllog.id'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
    )

def downgrade() -> None:
    op.drop_table('feedback')
    op.drop_index('ix_calllog_outcome_start', table_name='calllog')
    op.drop_index('ix_calllog_provider', table_name='calllog')
    op.drop_index('ix_calllog_outcome', table_name='calllog')
    op.drop_index('ix_calllog_start', table_name='calllog')
    op.drop_index('ix_calllog_load', table_name='calllog')
    op.drop_table('calllog')
    op.drop_index('ix_driver_phone', table_name='driver')
    op.drop_table('driver')
    op.drop_index('ix_agent_name', table_name='agent')
    op.drop_table('agent')
