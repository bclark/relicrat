-- Synthetic v0.1.0 upgrade fixture only. Ignore the three additive Games
-- columns (migration 0020); compare all pre-existing domain fields exactly.
-- Sessions/login rate limits change during browser checks and are not inventory.
WITH rows AS (
    SELECT 'owned_copies' AS name, to_jsonb(t) - 'game_contents' AS data FROM owned_copies t
    UNION ALL SELECT 'copy_detail_events', to_jsonb(t) - ARRAY['before_game_contents', 'after_game_contents'] FROM copy_detail_events t
    UNION ALL SELECT 'catalog_items', to_jsonb(t) FROM catalog_items t
    UNION ALL SELECT 'categories', to_jsonb(t) FROM categories t
    UNION ALL SELECT 'releases', to_jsonb(t) FROM releases t
    UNION ALL SELECT 'storage_locations', to_jsonb(t) FROM storage_locations t
    UNION ALL SELECT 'media_assets', to_jsonb(t) FROM media_assets t
    UNION ALL SELECT 'reconciliation_events', to_jsonb(t) FROM reconciliation_events t
    UNION ALL SELECT 'copy_location_events', to_jsonb(t) FROM copy_location_events t
    UNION ALL SELECT 'appearance_settings', to_jsonb(t) FROM appearance_settings t
    UNION ALL SELECT 'collection_settings', to_jsonb(t) FROM collection_settings t
    UNION ALL SELECT 'custom_collection_types', to_jsonb(t) FROM custom_collection_types t
    UNION ALL SELECT 'custom_type_revisions', to_jsonb(t) FROM custom_type_revisions t
    UNION ALL SELECT 'custom_collections', to_jsonb(t) FROM custom_collections t
    UNION ALL SELECT 'import_batches', to_jsonb(t) FROM import_batches t
    UNION ALL SELECT 'import_copies', to_jsonb(t) FROM import_copies t
    UNION ALL SELECT 'import_duplicate_decisions', to_jsonb(t) FROM import_duplicate_decisions t
    UNION ALL SELECT 'checklist_matches', to_jsonb(t) FROM checklist_matches t
    UNION ALL SELECT 'checklist_match_events', to_jsonb(t) FROM checklist_match_events t
    UNION ALL SELECT 'location_audits', to_jsonb(t) FROM location_audits t
    UNION ALL SELECT 'agent_credentials', to_jsonb(t) FROM agent_credentials t
)
SELECT json_build_object('table', name, 'rows', count(*), 'sha256',
    encode(sha256(convert_to(string_agg(data::text, E'\n' ORDER BY data::text), 'UTF8')), 'hex'))
FROM rows GROUP BY name ORDER BY name;
