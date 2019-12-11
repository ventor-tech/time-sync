"""empty message

Revision ID: 4d906cd9a206
Revises: 4f91f8e6df1a
Create Date: 2019-12-10 23:36:46.967859

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d906cd9a206'
down_revision = '4f91f8e6df1a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('default_target_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'users', 'connectors', ['default_target_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_column('users', 'default_target_id')
    # ### end Alembic commands ###
