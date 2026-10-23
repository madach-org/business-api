"""Add user ownership to customers, products and sales."""

from alembic import op
import sqlalchemy as sa

revision = "56db55f4aced"
down_revision = "4f6f1fabae53"
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable columns first so existing records are preserved.
    with op.batch_alter_table("customers") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_customers_user_id", ["user_id"])
        batch_op.create_foreign_key(
            "fk_customers_user_id_users", "users", ["user_id"], ["id"]
        )

    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_products_user_id", ["user_id"])
        batch_op.create_foreign_key(
            "fk_products_user_id_users", "users", ["user_id"], ["id"]
        )

    with op.batch_alter_table("sales") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_sales_user_id", ["user_id"])
        batch_op.create_foreign_key(
            "fk_sales_user_id_users", "users", ["user_id"], ["id"]
        )

    # Assign all existing records to User 1.
    op.execute("UPDATE customers SET user_id = 1 WHERE user_id IS NULL")
    op.execute("UPDATE products SET user_id = 1 WHERE user_id IS NULL")
    op.execute("UPDATE sales SET user_id = 1 WHERE user_id IS NULL")

    # Require an owner for all future records.
    with op.batch_alter_table("customers") as batch_op:
        batch_op.alter_column(
            "user_id", existing_type=sa.Integer(), nullable=False
        )

    with op.batch_alter_table("products") as batch_op:
        batch_op.alter_column(
            "user_id", existing_type=sa.Integer(), nullable=False
        )

    with op.batch_alter_table("sales") as batch_op:
        batch_op.alter_column(
            "user_id", existing_type=sa.Integer(), nullable=False
        )


def downgrade():
    with op.batch_alter_table("sales") as batch_op:
        batch_op.drop_constraint("fk_sales_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_sales_user_id")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_constraint("fk_products_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_products_user_id")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("customers") as batch_op:
        batch_op.drop_constraint("fk_customers_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_customers_user_id")
        batch_op.drop_column("user_id")
