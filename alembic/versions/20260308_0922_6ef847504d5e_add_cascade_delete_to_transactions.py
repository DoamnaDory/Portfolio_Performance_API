"""add_cascade_delete_to_transactions

Revision ID: 6ef847504d5e
Revises: f76455672b3e
Create Date: 2026-03-08 09:22:12.294314

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers...
revision = '...'
down_revision = 'f76455672b3e'  # ссылка на предыдущую миграцию


# ...

def upgrade():
    op.drop_constraint('transactions_portfolio_id_fkey', 'transactions',
                       type_='foreignkey')

    op.create_foreign_key(
        'transactions_portfolio_id_fkey',
        'transactions', 'portfolios',
        ['portfolio_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    op.drop_constraint('transactions_portfolio_id_fkey', 'transactions',
                       type_='foreignkey')
    op.create_foreign_key(
        'transactions_portfolio_id_fkey',
        'transactions', 'portfolios',
        ['portfolio_id'], ['id']
    )
