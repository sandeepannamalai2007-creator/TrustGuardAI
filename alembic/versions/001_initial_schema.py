"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-21 15:15:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. students
    op.create_table(
        'students',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('student_id')
    )
    op.create_index(op.f('ix_students_id'), 'students', ['id'], unique=False)

    # 2. behavior_profiles
    op.create_table(
        'behavior_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=True),
        sa.Column('avg_dwell_time', sa.Float(), nullable=True),
        sa.Column('avg_flight_time', sa.Float(), nullable=True),
        sa.Column('typing_speed', sa.Float(), nullable=True),
        sa.Column('mouse_velocity', sa.Float(), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=True),
        sa.Column('enrollment_status', sa.String(), nullable=True),
        sa.Column('enrollment_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_behavior_profiles_id'), 'behavior_profiles', ['id'], unique=False)

    # 3. enrollment_buffers
    op.create_table(
        'enrollment_buffers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('avg_dwell_time', sa.Float(), nullable=False),
        sa.Column('avg_flight_time', sa.Float(), nullable=False),
        sa.Column('typing_speed', sa.Float(), nullable=False),
        sa.Column('mouse_velocity', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_enrollment_buffers_id'), 'enrollment_buffers', ['id'], unique=False)

    # 4. exam_sessions
    op.create_table(
        'exam_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exam_sessions_id'), 'exam_sessions', ['id'], unique=False)

    # 5. trust_logs
    op.create_table(
        'trust_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('trust_score', sa.Float(), nullable=True),
        sa.Column('decision_score', sa.Float(), nullable=True),
        sa.Column('avg_dwell', sa.Float(), nullable=True),
        sa.Column('avg_flight', sa.Float(), nullable=True),
        sa.Column('typing_speed', sa.Float(), nullable=True),
        sa.Column('avg_mouse_velocity', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['exam_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trust_logs_id'), 'trust_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('trust_logs')
    op.drop_table('exam_sessions')
    op.drop_table('enrollment_buffers')
    op.drop_table('behavior_profiles')
    op.drop_table('students')
