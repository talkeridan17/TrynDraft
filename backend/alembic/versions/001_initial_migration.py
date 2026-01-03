"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('summoner_name', sa.String(), nullable=True),
        sa.Column('region', sa.String(), nullable=True, default='NA'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_premium', sa.Boolean(), nullable=True, default=False),
        sa.Column('preferences', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create drafts table
    op.create_table('drafts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('game_mode', sa.String(), nullable=True, default='DRAFT'),
        sa.Column('side', sa.String(), nullable=True, default='BLUE'),
        sa.Column('role', sa.String(), nullable=True, default='TOP'),
        sa.Column('elo', sa.String(), nullable=True, default='PLATINUM'),
        sa.Column('region', sa.String(), nullable=True, default='NA'),
        sa.Column('patch', sa.String(), nullable=True, default='14.4.1'),
        sa.Column('phase', sa.String(), nullable=True, default='BAN'),
        sa.Column('current_turn', sa.Integer(), nullable=True, default=0),
        sa.Column('bans_blue', sa.JSON(), nullable=True),
        sa.Column('bans_red', sa.JSON(), nullable=True),
        sa.Column('picks_blue', sa.JSON(), nullable=True),
        sa.Column('picks_red', sa.JSON(), nullable=True),
        sa.Column('analysis', sa.Text(), nullable=True),
        sa.Column('win_prediction', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_champion_pool table
    op.create_table('user_champion_pool',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('champion_name', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('proficiency', sa.Integer(), nullable=True, default=1),
        sa.Column('is_favorite', sa.Boolean(), nullable=True, default=False),
        sa.Column('games_played', sa.Integer(), nullable=True, default=0),
        sa.Column('win_rate', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create champions table
    op.create_table('champions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('roles', sa.JSON(), nullable=True),
        sa.Column('attack', sa.Integer(), nullable=True),
        sa.Column('defense', sa.Integer(), nullable=True),
        sa.Column('magic', sa.Integer(), nullable=True),
        sa.Column('difficulty', sa.Integer(), nullable=True),
        sa.Column('patch', sa.String(), nullable=True),
        sa.Column('win_rate', sa.Integer(), nullable=True),
        sa.Column('pick_rate', sa.Integer(), nullable=True),
        sa.Column('ban_rate', sa.Integer(), nullable=True),
        sa.Column('synergies', sa.JSON(), nullable=True),
        sa.Column('counters', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('champions')
    op.drop_table('user_champion_pool')
    op.drop_table('drafts')
    op.drop_table('users')