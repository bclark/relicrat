"""Independent storage revisions, retained movements and serialized acyclic hierarchy.

Downgrade discards movement history/revisions and cycle protection, retaining
current assignments. Capture and verify a quiescent DB/media backup first.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0003_storage"
down_revision = "0002_reconciliation"
branch_labels = None
depends_on = None


def upgrade():
    # Block graph writes until validation and trigger installation commit together.
    op.execute("LOCK TABLE storage_locations IN ACCESS EXCLUSIVE MODE")
    op.execute("""
        CREATE FUNCTION check_storage_graph() RETURNS void LANGUAGE plpgsql AS $$
        BEGIN
            IF EXISTS (
                WITH RECURSIVE paths AS (
                    SELECT id, parent_id, ARRAY[id] AS visited, false AS cycle FROM storage_locations
                    UNION ALL
                    SELECT p.id, s.parent_id, p.visited || s.id, s.id = ANY(p.visited)
                    FROM paths p JOIN storage_locations s ON s.id = p.parent_id
                    WHERE NOT p.cycle
                ) SELECT 1 FROM paths WHERE cycle
            ) THEN
                RAISE EXCEPTION 'storage location hierarchy contains a cycle; repair topology before migration or mutation'
                    USING ERRCODE = '23514';
            END IF;
        END $$
    """)
    op.execute("SELECT check_storage_graph()")
    op.create_table("storage_hierarchy_guard",
                    sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
                    sa.CheckConstraint("id = 1", name="storage_guard_singleton"))
    op.execute("INSERT INTO storage_hierarchy_guard (id) VALUES (1)")
    op.execute("""
        CREATE FUNCTION serialize_storage_graph() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            UPDATE storage_hierarchy_guard SET generation = 1 - generation WHERE id = 1;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'storage hierarchy coordination row is missing' USING ERRCODE = '23514';
            END IF;
            RETURN NULL;
        END $$
    """)
    op.execute("""
        CREATE FUNCTION validate_storage_graph() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM check_storage_graph();
            RETURN NULL;
        END $$
    """)
    # The actual write forces stale REPEATABLE READ snapshots to serialize-fail.
    # Volatile trigger queries obtain fresh command visibility at READ COMMITTED.
    op.execute("CREATE TRIGGER storage_graph_serialize BEFORE INSERT OR UPDATE OR DELETE ON storage_locations FOR EACH STATEMENT EXECUTE FUNCTION serialize_storage_graph()")
    op.execute("CREATE TRIGGER storage_graph_validate AFTER INSERT OR UPDATE ON storage_locations FOR EACH STATEMENT EXECUTE FUNCTION validate_storage_graph()")
    op.add_column("owned_copies", sa.Column("storage_revision", sa.Integer(), nullable=False, server_default="0"))
    op.create_check_constraint("storage_revision_nonnegative", "owned_copies", "storage_revision >= 0")
    op.create_table("copy_location_events",
                    sa.Column("id", UUID(as_uuid=True), primary_key=True),
                    sa.Column("owned_copy_id", UUID(as_uuid=True), sa.ForeignKey("owned_copies.id", ondelete="RESTRICT"), nullable=False),
                    sa.Column("before_location_id", UUID(as_uuid=True), sa.ForeignKey("storage_locations.id", ondelete="RESTRICT")),
                    sa.Column("after_location_id", UUID(as_uuid=True), sa.ForeignKey("storage_locations.id", ondelete="RESTRICT")),
                    sa.Column("before_revision", sa.Integer(), nullable=False),
                    sa.Column("after_revision", sa.Integer(), nullable=False),
                    sa.Column("operation", sa.String(30), nullable=False, server_default="manual"),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
                    sa.UniqueConstraint("owned_copy_id", "after_revision"),
                    sa.CheckConstraint("before_revision >= 0 AND after_revision = before_revision + 1", name="location_revision_step"),
                    sa.CheckConstraint("operation = 'manual'", name="location_manual"),
                    sa.CheckConstraint("before_location_id IS DISTINCT FROM after_location_id", name="location_changed"))


def downgrade():
    op.drop_table("copy_location_events")
    op.drop_constraint("storage_revision_nonnegative", "owned_copies", type_="check")
    op.drop_column("owned_copies", "storage_revision")
    op.execute("DROP TRIGGER storage_graph_serialize ON storage_locations")
    op.execute("DROP TRIGGER storage_graph_validate ON storage_locations")
    op.execute("DROP FUNCTION serialize_storage_graph()")
    op.execute("DROP FUNCTION validate_storage_graph()")
    op.execute("DROP FUNCTION check_storage_graph()")
    op.drop_table("storage_hierarchy_guard")
