"""Immutable custom definitions/checklists and audited personal observations.

Downgrade refuses any custom data; use verified recovery instead of losing it.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '0014_custom_collections'
down_revision = '0013_movies'
branch_labels = None
depends_on = None
OLD_CHANGE = 'before_title IS DISTINCT FROM after_title OR before_edition_label IS DISTINCT FROM after_edition_label OR before_collection_type IS DISTINCT FROM after_collection_type OR before_record_details IS DISTINCT FROM after_record_details OR before_comic_details IS DISTINCT FROM after_comic_details OR before_barcode IS DISTINCT FROM after_barcode OR before_movie_details IS DISTINCT FROM after_movie_details'


def upgrade():
    op.create_table('custom_collection_types',
        sa.Column('id', sa.String(60), primary_key=True),
        sa.Column('definition', JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("id ~ '^[a-z][a-z0-9_-]{0,59}$' AND id NOT IN ('other','record','comic','movie')", name='custom_type_id_valid'),
        sa.CheckConstraint("(jsonb_typeof(definition) = 'object' AND definition->>'id' = id AND jsonb_typeof(definition->'optional_fields') = 'array' AND jsonb_array_length(definition->'optional_fields') <= 12 AND (definition->'title'->>'max_length')::int BETWEEN 1 AND 500) IS TRUE", name='custom_type_definition_valid'))
    op.create_table('custom_collections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('slug', sa.String(60), nullable=False, unique=True),
        sa.Column('type_id', sa.String(60), sa.ForeignKey('custom_collection_types.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('proposal', JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("slug ~ '^[a-z][a-z0-9_-]{0,59}$'", name='custom_collection_slug_valid'),
        sa.CheckConstraint("(jsonb_typeof(proposal) = 'object' AND proposal->'collection'->>'id' = slug AND proposal->'collection'->>'type_id' = type_id) IS TRUE", name='custom_collection_proposal_valid'))
    op.add_column('owned_copies', sa.Column('custom_collection_id', UUID(as_uuid=True), sa.ForeignKey('custom_collections.id', ondelete='RESTRICT')))
    op.create_index('ix_owned_copies_custom_collection_id','owned_copies',['custom_collection_id'])
    op.add_column('owned_copies', sa.Column('custom_details', JSONB(), nullable=False, server_default='{}'))
    op.add_column('owned_copies', sa.Column('custom_intake_hash', sa.String(64)))
    op.create_check_constraint('custom_copy_valid','owned_copies',"jsonb_typeof(custom_details) = 'object' AND ((custom_collection_id IS NULL AND custom_details = '{}'::jsonb AND custom_intake_hash IS NULL) OR (custom_collection_id IS NOT NULL AND collection_type = 'other' AND custom_intake_hash ~ '^[0-9a-f]{64}$'))")
    for key in ('before_custom_details','after_custom_details'):
        op.add_column('copy_detail_events', sa.Column(key,JSONB()))
    op.drop_constraint('details_changed','copy_detail_events',type_='check')
    op.create_check_constraint('details_changed','copy_detail_events',OLD_CHANGE+' OR before_custom_details IS DISTINCT FROM after_custom_details')
    op.execute("""
CREATE FUNCTION relicrat_immutable_collection() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 RAISE EXCEPTION 'Custom definitions and collections are immutable; retain their history' USING ERRCODE='23514';
END $$;
CREATE TRIGGER immutable_custom_type BEFORE UPDATE OR DELETE ON custom_collection_types FOR EACH ROW EXECUTE FUNCTION relicrat_immutable_collection();
CREATE TRIGGER immutable_custom_collection BEFORE UPDATE OR DELETE ON custom_collections FOR EACH ROW EXECUTE FUNCTION relicrat_immutable_collection();
CREATE FUNCTION relicrat_validate_custom_copy() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE definition jsonb; field jsonb; key text; value jsonb;
BEGIN
 IF TG_OP='UPDATE' AND (NEW.custom_collection_id IS DISTINCT FROM OLD.custom_collection_id OR NEW.custom_intake_hash IS DISTINCT FROM OLD.custom_intake_hash) THEN
  RAISE EXCEPTION 'Custom collection membership and intake identity are immutable' USING ERRCODE='23514';
 END IF;
 IF NEW.custom_collection_id IS NOT NULL THEN
  SELECT t.definition INTO definition FROM custom_collections c JOIN custom_collection_types t ON t.id=c.type_id WHERE c.id=NEW.custom_collection_id;
  IF definition IS NULL THEN RAISE EXCEPTION 'Unknown custom collection' USING ERRCODE='23503'; END IF;
  IF NEW.collection_type <> 'other' OR NEW.custom_intake_hash IS NULL OR NEW.provisional_title IS NULL OR length(btrim(NEW.provisional_title))=0 OR length(NEW.provisional_title) > (definition->'title'->>'max_length')::int THEN
   RAISE EXCEPTION 'Custom figure requires a bounded title and its original type' USING ERRCODE='23514';
  END IF;
  IF jsonb_typeof(NEW.custom_details) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'Custom fields must be an object' USING ERRCODE='23514'; END IF;
  FOR key,value IN SELECT * FROM jsonb_each(NEW.custom_details) LOOP
   SELECT f INTO field FROM jsonb_array_elements(definition->'optional_fields') f WHERE f->>'id'=key;
   IF field IS NULL OR jsonb_typeof(value) <> 'string' OR length(btrim(value#>>'{}'))=0 OR length(value#>>'{}') > (field->>'max_length')::int THEN
    RAISE EXCEPTION 'Unknown or invalid custom observation' USING ERRCODE='23514';
   END IF;
  END LOOP;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER custom_copy_fields BEFORE INSERT OR UPDATE ON owned_copies FOR EACH ROW EXECUTE FUNCTION relicrat_validate_custom_copy();
""")


def downgrade():
    op.execute('LOCK TABLE custom_collection_types, custom_collections, owned_copies, copy_detail_events IN ACCESS EXCLUSIVE MODE')
    populated=op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM custom_collection_types) OR EXISTS(SELECT 1 FROM custom_collections) OR EXISTS(SELECT 1 FROM owned_copies WHERE custom_collection_id IS NOT NULL OR custom_details <> '{}'::jsonb) OR EXISTS(SELECT 1 FROM copy_detail_events WHERE before_custom_details IS NOT NULL OR after_custom_details IS NOT NULL)")).scalar()
    if populated:
        raise RuntimeError('Custom collection data exists; downgrade would lose history. Use verified recovery.')
    op.execute('DROP TRIGGER custom_copy_fields ON owned_copies; DROP FUNCTION relicrat_validate_custom_copy(); DROP TRIGGER immutable_custom_collection ON custom_collections; DROP TRIGGER immutable_custom_type ON custom_collection_types; DROP FUNCTION relicrat_immutable_collection()')
    op.drop_constraint('details_changed','copy_detail_events',type_='check')
    op.create_check_constraint('details_changed','copy_detail_events',OLD_CHANGE)
    for key in ('before_custom_details','after_custom_details'):op.drop_column('copy_detail_events',key)
    op.drop_constraint('custom_copy_valid','owned_copies',type_='check')
    op.drop_column('owned_copies','custom_intake_hash')
    op.drop_column('owned_copies','custom_details')
    op.drop_index('ix_owned_copies_custom_collection_id',table_name='owned_copies')
    op.drop_column('owned_copies','custom_collection_id')
    op.drop_table('custom_collections')
    op.drop_table('custom_collection_types')
