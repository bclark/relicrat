"""Explicit checklist matches, retained history and owner-confirmed progress."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision = '0016_checklist_progress'
down_revision = '0015_custom_field_controls'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('checklist_matches',
        sa.Column('owned_copy_id', UUID(as_uuid=True), sa.ForeignKey('owned_copies.id', ondelete='RESTRICT'), primary_key=True),
        sa.Column('collection_id', UUID(as_uuid=True), sa.ForeignKey('custom_collections.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('entry_id', sa.String(60)), sa.Column('confirmed', sa.Boolean(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('revision >= 1', name='checklist_match_revision'),
        sa.CheckConstraint('entry_id IS NOT NULL OR NOT confirmed', name='checklist_match_confirmation'))
    op.create_index('ix_checklist_matches_collection_entry', 'checklist_matches', ['collection_id', 'entry_id'])
    op.create_table('checklist_match_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('owned_copy_id', UUID(as_uuid=True), sa.ForeignKey('owned_copies.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('collection_id', UUID(as_uuid=True), sa.ForeignKey('custom_collections.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('before_entry_id', sa.String(60)), sa.Column('after_entry_id', sa.String(60)),
        sa.Column('before_confirmed', sa.Boolean(), nullable=False), sa.Column('after_confirmed', sa.Boolean(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('owned_copy_id', 'revision', name='checklist_event_revision'),
        sa.CheckConstraint('revision >= 1', name='checklist_event_positive'),
        sa.CheckConstraint('(before_entry_id IS NOT NULL OR NOT before_confirmed) AND (after_entry_id IS NOT NULL OR NOT after_confirmed)', name='checklist_event_confirmation'))
    op.execute("""
CREATE FUNCTION relicrat_checklist_match() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE member uuid; ownership text; removed timestamptz; proposal jsonb;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Clear a checklist match and retain its history' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (NEW.owned_copy_id IS DISTINCT FROM OLD.owned_copy_id OR NEW.collection_id IS DISTINCT FROM OLD.collection_id) THEN
  RAISE EXCEPTION 'Checklist match identity is immutable' USING ERRCODE='23514';
 END IF;
 SELECT custom_collection_id,ownership_status,deleted_at INTO member,ownership,removed FROM owned_copies WHERE id=NEW.owned_copy_id FOR UPDATE;
 IF member IS NULL OR member IS DISTINCT FROM NEW.collection_id THEN RAISE EXCEPTION 'Checklist match must belong to the copy collection' USING ERRCODE='23514'; END IF;
 IF NEW.entry_id IS NOT NULL THEN
  IF ownership<>'owned' OR removed IS NOT NULL THEN RAISE EXCEPTION 'Only active owned copies can receive a checklist match' USING ERRCODE='23514'; END IF;
  SELECT c.proposal INTO proposal FROM custom_collections c WHERE c.id=member;
  IF NOT EXISTS(SELECT 1 FROM jsonb_array_elements(proposal->'collection'->'checklist') e WHERE e->>'id'=NEW.entry_id) THEN
   RAISE EXCEPTION 'Checklist entry is not in this collection' USING ERRCODE='23514';
  END IF;
 END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.revision<>1 OR NEW.entry_id IS NULL THEN RAISE EXCEPTION 'Initial match requires an entry and revision one' USING ERRCODE='23514'; END IF;
 ELSE
  IF NEW.revision<>OLD.revision+1 OR (NEW.entry_id IS NOT DISTINCT FROM OLD.entry_id AND NEW.confirmed=OLD.confirmed) THEN
   RAISE EXCEPTION 'Checklist change requires the next revision' USING ERRCODE='23514';
  END IF;
 END IF;
 NEW.updated_at=statement_timestamp();
 RETURN NEW;
END $$;
CREATE TRIGGER checklist_match_guard BEFORE INSERT OR UPDATE OR DELETE ON checklist_matches FOR EACH ROW EXECUTE FUNCTION relicrat_checklist_match();
CREATE FUNCTION relicrat_checklist_history() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 INSERT INTO checklist_match_events(owned_copy_id,collection_id,before_entry_id,after_entry_id,before_confirmed,after_confirmed,revision)
 VALUES(NEW.owned_copy_id,NEW.collection_id,CASE WHEN TG_OP='UPDATE' THEN OLD.entry_id ELSE NULL END,NEW.entry_id,CASE WHEN TG_OP='UPDATE' THEN OLD.confirmed ELSE false END,NEW.confirmed,NEW.revision);
 RETURN NEW;
END $$;
CREATE TRIGGER checklist_match_history AFTER INSERT OR UPDATE ON checklist_matches FOR EACH ROW EXECUTE FUNCTION relicrat_checklist_history();
CREATE TRIGGER immutable_checklist_history BEFORE UPDATE OR DELETE ON checklist_match_events FOR EACH ROW EXECUTE FUNCTION relicrat_immutable_collection();
""")


def downgrade():
    op.execute('LOCK TABLE checklist_matches, checklist_match_events IN ACCESS EXCLUSIVE MODE')
    populated = op.get_bind().execute(sa.text('SELECT EXISTS(SELECT 1 FROM checklist_matches) OR EXISTS(SELECT 1 FROM checklist_match_events)')).scalar()
    if populated:
        raise RuntimeError('Checklist matches or history exist; downgrade would lose review history. Use verified recovery.')
    op.execute('DROP TRIGGER immutable_checklist_history ON checklist_match_events; DROP TRIGGER checklist_match_history ON checklist_matches; DROP FUNCTION relicrat_checklist_history(); DROP TRIGGER checklist_match_guard ON checklist_matches; DROP FUNCTION relicrat_checklist_match()')
    op.drop_table('checklist_match_events')
    op.drop_index('ix_checklist_matches_collection_entry', table_name='checklist_matches')
    op.drop_table('checklist_matches')
