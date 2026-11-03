"""Typed custom observations and append-only, compatible field revisions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0015_custom_field_controls'
down_revision='0014_custom_collections'
branch_labels=None
depends_on=None

SQL=r"""
CREATE FUNCTION relicrat_custom_definition_valid(d jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE f jsonb; option jsonb; n int;
BEGIN
 IF jsonb_typeof(d) IS DISTINCT FROM 'object' OR jsonb_typeof(d->'optional_fields') IS DISTINCT FROM 'array' THEN RETURN false; END IF;
 IF NOT ((d->'title'->>'max_length')::int BETWEEN 1 AND 500) IS TRUE OR jsonb_array_length(d->'optional_fields')>12 THEN RETURN false; END IF;
 IF (SELECT count(DISTINCT v->>'id') FROM jsonb_array_elements(d->'optional_fields') v)<>jsonb_array_length(d->'optional_fields') THEN RETURN false; END IF;
 FOR f IN SELECT * FROM jsonb_array_elements(d->'optional_fields') LOOP
  IF NOT ((f->>'id') ~ '^[a-z][a-z0-9_-]{0,59}$') IS TRUE OR f->>'id' IN ('title','notes','photos','storage-location','storage_location') OR NOT ((f->>'max_length')::int BETWEEN 1 AND 2000) IS TRUE OR f->>'input' IS NULL OR f->>'input' NOT IN ('text','select','radio','checkbox','checkboxes') THEN RETURN false; END IF;
  IF jsonb_typeof(COALESCE(f->'options','[]'::jsonb)) IS DISTINCT FROM 'array' THEN RETURN false; END IF;
  n=jsonb_array_length(COALESCE(f->'options','[]'::jsonb));
  IF f->>'input' IN ('select','radio','checkboxes') THEN
   IF n<1 OR n>20 OR (SELECT count(DISTINCT lower(v#>>'{}')) FROM jsonb_array_elements(f->'options') v)<>n THEN RETURN false; END IF;
   FOR option IN SELECT * FROM jsonb_array_elements(f->'options') LOOP
    IF jsonb_typeof(option)<>'string' OR NOT ((option#>>'{}') ~ '[^[:space:]]') OR length(option#>>'{}')>(f->>'max_length')::int THEN RETURN false; END IF;
   END LOOP;
  ELSIF n<>0 THEN RETURN false;
  END IF;
 END LOOP;
 RETURN true;
END $$;
CREATE FUNCTION relicrat_custom_values_valid(d jsonb,title text,details jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE f jsonb; key text; value jsonb; choice jsonb;
BEGIN
 IF title IS NULL OR NOT (title ~ '[^[:space:]]') OR length(title)>(d->'title'->>'max_length')::int OR jsonb_typeof(details) IS DISTINCT FROM 'object' THEN RETURN false; END IF;
 FOR key,value IN SELECT * FROM jsonb_each(details) LOOP
  SELECT v INTO f FROM jsonb_array_elements(d->'optional_fields') v WHERE v->>'id'=key;
  IF f IS NULL THEN RETURN false; END IF;
  IF f->>'input'='checkbox' THEN
   IF jsonb_typeof(value)<>'boolean' THEN RETURN false; END IF;
  ELSIF f->>'input'='checkboxes' THEN
   IF jsonb_typeof(value)<>'array' THEN RETURN false; END IF;
   IF jsonb_array_length(value)>20 OR (SELECT count(DISTINCT v) FROM jsonb_array_elements(value) v)<>jsonb_array_length(value) THEN RETURN false; END IF;
   FOR choice IN SELECT * FROM jsonb_array_elements(value) LOOP
    IF jsonb_typeof(choice)<>'string' OR NOT ((f->'options') @> jsonb_build_array(choice)) THEN RETURN false; END IF;
   END LOOP;
  ELSE
   IF jsonb_typeof(value)<>'string' OR NOT ((value#>>'{}') ~ '[^[:space:]]') OR length(value#>>'{}')>(f->>'max_length')::int THEN RETURN false; END IF;
   IF f->>'input' IN ('select','radio') AND NOT ((f->'options') @> jsonb_build_array(value)) THEN RETURN false; END IF;
  END IF;
 END LOOP;
 RETURN true;
END $$;
CREATE FUNCTION relicrat_custom_base_definition() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT relicrat_custom_definition_valid(NEW.definition) THEN RAISE EXCEPTION 'Invalid custom field definition' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER custom_base_definition BEFORE INSERT ON custom_collection_types FOR EACH ROW EXECUTE FUNCTION relicrat_custom_base_definition();
CREATE FUNCTION relicrat_custom_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE next_revision int;
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended('relicrat-custom-type:'||NEW.type_id,0));
 SELECT COALESCE(max(revision),0)+1 INTO next_revision FROM custom_type_revisions WHERE type_id=NEW.type_id;
 IF NEW.revision<>next_revision OR NEW.definition->>'id' IS DISTINCT FROM NEW.type_id OR NOT relicrat_custom_definition_valid(NEW.definition) THEN RAISE EXCEPTION 'Invalid or stale custom definition revision' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM owned_copies o JOIN custom_collections c ON c.id=o.custom_collection_id WHERE c.type_id=NEW.type_id AND NOT relicrat_custom_values_valid(NEW.definition,o.provisional_title,o.custom_details)) THEN
  RAISE EXCEPTION 'Definition revision would invalidate saved observations' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER custom_revision_insert BEFORE INSERT ON custom_type_revisions FOR EACH ROW EXECUTE FUNCTION relicrat_custom_revision();
CREATE TRIGGER immutable_custom_revision BEFORE UPDATE OR DELETE ON custom_type_revisions FOR EACH ROW EXECUTE FUNCTION relicrat_immutable_collection();
CREATE OR REPLACE FUNCTION relicrat_validate_custom_copy() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE definition jsonb; type_key text;
BEGIN
 IF TG_OP='UPDATE' AND (NEW.custom_collection_id IS DISTINCT FROM OLD.custom_collection_id OR NEW.custom_intake_hash IS DISTINCT FROM OLD.custom_intake_hash) THEN
  RAISE EXCEPTION 'Custom collection membership and intake identity are immutable' USING ERRCODE='23514';
 END IF;
 IF NEW.custom_collection_id IS NOT NULL THEN
  SELECT type_id INTO type_key FROM custom_collections WHERE id=NEW.custom_collection_id;
  IF type_key IS NULL THEN RAISE EXCEPTION 'Unknown custom collection' USING ERRCODE='23503'; END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended('relicrat-custom-type:'||type_key,0));
  SELECT r.definition INTO definition FROM custom_type_revisions r WHERE r.type_id=type_key ORDER BY r.revision DESC LIMIT 1;
  IF definition IS NULL THEN SELECT t.definition INTO definition FROM custom_collection_types t WHERE t.id=type_key; END IF;
  IF NEW.collection_type<>'other' OR NEW.custom_intake_hash IS NULL OR NOT relicrat_custom_values_valid(definition,NEW.provisional_title,NEW.custom_details) THEN RAISE EXCEPTION 'Invalid custom observations' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
"""


def upgrade():
    op.create_table('custom_type_revisions',
        sa.Column('type_id',sa.String(60),sa.ForeignKey('custom_collection_types.id',ondelete='RESTRICT'),primary_key=True),
        sa.Column('revision',sa.Integer(),primary_key=True),sa.Column('definition',JSONB(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.CheckConstraint('revision >= 1',name='custom_revision_positive'))
    op.execute(SQL)


def downgrade():
    op.execute('LOCK TABLE custom_collection_types, custom_type_revisions, owned_copies, copy_detail_events IN ACCESS EXCLUSIVE MODE')
    changed=op.get_bind().execute(sa.text("""SELECT EXISTS(SELECT 1 FROM custom_type_revisions)
    OR EXISTS(SELECT 1 FROM custom_collection_types t, jsonb_array_elements(t.definition->'optional_fields') f WHERE f->>'input'<>'text')
    OR EXISTS(SELECT 1 FROM owned_copies o,jsonb_each(o.custom_details) v WHERE jsonb_typeof(v.value)<>'string')
    OR EXISTS(SELECT 1 FROM copy_detail_events e,jsonb_each(COALESCE(e.before_custom_details,'{}'::jsonb)) v WHERE jsonb_typeof(v.value)<>'string')
    OR EXISTS(SELECT 1 FROM copy_detail_events e,jsonb_each(COALESCE(e.after_custom_details,'{}'::jsonb)) v WHERE jsonb_typeof(v.value)<>'string')""")).scalar()
    if changed:raise RuntimeError('Typed observations or definition revisions exist; downgrade would lose history. Use verified recovery.')
    op.execute('DROP TRIGGER custom_base_definition ON custom_collection_types; DROP FUNCTION relicrat_custom_base_definition(); DROP TRIGGER custom_revision_insert ON custom_type_revisions; DROP TRIGGER immutable_custom_revision ON custom_type_revisions; DROP FUNCTION relicrat_custom_revision()')
    op.execute(OLD_COPY_TRIGGER)
    op.execute('DROP FUNCTION relicrat_custom_values_valid(jsonb,text,jsonb); DROP FUNCTION relicrat_custom_definition_valid(jsonb)')
    op.drop_table('custom_type_revisions')


OLD_COPY_TRIGGER = "CREATE OR REPLACE FUNCTION relicrat_validate_custom_copy() RETURNS trigger LANGUAGE plpgsql AS $$\nDECLARE definition jsonb; field jsonb; key text; value jsonb;\nBEGIN\n IF TG_OP='UPDATE' AND (NEW.custom_collection_id IS DISTINCT FROM OLD.custom_collection_id OR NEW.custom_intake_hash IS DISTINCT FROM OLD.custom_intake_hash) THEN\n  RAISE EXCEPTION 'Custom collection membership and intake identity are immutable' USING ERRCODE='23514';\n END IF;\n IF NEW.custom_collection_id IS NOT NULL THEN\n  SELECT t.definition INTO definition FROM custom_collections c JOIN custom_collection_types t ON t.id=c.type_id WHERE c.id=NEW.custom_collection_id;\n  IF definition IS NULL THEN RAISE EXCEPTION 'Unknown custom collection' USING ERRCODE='23503'; END IF;\n  IF NEW.collection_type <> 'other' OR NEW.custom_intake_hash IS NULL OR NEW.provisional_title IS NULL OR length(btrim(NEW.provisional_title))=0 OR length(NEW.provisional_title) > (definition->'title'->>'max_length')::int THEN\n   RAISE EXCEPTION 'Custom figure requires a bounded title and its original type' USING ERRCODE='23514';\n  END IF;\n  IF jsonb_typeof(NEW.custom_details) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'Custom fields must be an object' USING ERRCODE='23514'; END IF;\n  FOR key,value IN SELECT * FROM jsonb_each(NEW.custom_details) LOOP\n   SELECT f INTO field FROM jsonb_array_elements(definition->'optional_fields') f WHERE f->>'id'=key;\n   IF field IS NULL OR jsonb_typeof(value) <> 'string' OR length(btrim(value#>>'{}'))=0 OR length(value#>>'{}') > (field->>'max_length')::int THEN\n    RAISE EXCEPTION 'Unknown or invalid custom observation' USING ERRCODE='23514';\n   END IF;\n  END LOOP;\n END IF;\n RETURN NEW;\nEND $$;\n"
