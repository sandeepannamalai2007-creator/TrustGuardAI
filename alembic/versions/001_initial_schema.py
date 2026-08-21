"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-21 14:20:00.000000

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
    op.create_table(
        'students',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_students_id'), 'students', ['id'], unique=False)
    op.create_index(op.f('ix_students_student_id'), 'students', ['student_id'], unique=True)

    op.create_table(
        'exam_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exam_sessions_id'), 'exam_sessions', ['id'], unique=False)

    op.create_table(
        'behavior_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('baseline_dwell_time', sa.Float(), nullable=True),
        sa.Column('baseline_flight_time', sa.Float(), nullable=True),
        sa.Column('baseline_typing_speed', sa.Float(), nullable=True),
        sa.Column('baseline_mouse_velocity', sa.Float(), nullable=True),
        sa.Column('std_dwell_time', sa.Float(), nullable=True),
        sa.Column('std_flight_time', sa.Float(), nullable=True),
        sa.Column('std_typing_speed', sa.Float(), nullable=True),
        sa.Column('std_mouse_velocity', sa.Float(), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=True),
        sa.Column('enrollment_status', sa.String(), nullable=True),
        sa.Column('enrollment_count', sa.Integer(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id')
    )
    op.create_index(op.f('ix_behavior_profiles_id'), 'behavior_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_behavior_profiles_user_id'), 'behavior_profiles', ['user_id'], unique=False)

    op.create_table(
        'trust_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('exam_session_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('avg_dwell', sa.Float(), nullable=True),
        sa.Column('avg_flight', sa.Float(), nullable=True),
        sa.Column('typing_speed', sa.Float(), nullable=True),
        sa.Column('mouse_velocity', sa.Float(), nullable=True),
        sa.Column('keystroke_count', sa.Integer(), nullable=True),
        sa.Column('std_dwell', sa.Float(), nullable=True),
        sa.Column('std_flight', sa.Float(), nullable=True),
        sa.Column('df_ratio', sa.Float(), nullable=True),
        sa.Column('pause_count', sa.Integer(), nullable=True),
        sa.Column('trust_score', sa.Float(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('decision_score', sa.Float(), nullable=False),
        sa.Column('security_state', sa.String(), nullable=True),
        sa.Column('high_trust_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['exam_session_id'], ['exam_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trust_logs_id'), 'trust_logs', ['id'], unique=False)
    op.create_index(op.f('ix_trust_logs_session_id'), 'trust_logs', ['session_id'], unique=False)
    op.create_index(op.f('ix_trust_logs_user_id'), 'trust_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('trust_logs')
    op.drop_table('behavior_profiles')
    op.drop_table('exam_sessions')
    op.drop_table('students')
