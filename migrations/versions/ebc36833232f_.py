"""empty message

Revision ID: ebc36833232f
Revises: 4d906cd9a206
Create Date: 2020-01-10 15:50:56.523460

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ebc36833232f'
down_revision = '4d906cd9a206'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('worklogs', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'worklogs', 'worklogs', ['parent_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'worklogs', type_='foreignkey')
    op.drop_column('worklogs', 'parent_id')
    # ### end Alembic commands ###
