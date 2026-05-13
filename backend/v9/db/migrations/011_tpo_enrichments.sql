-- P-TPO-A.1: TPO enrichment columns
ALTER TABLE v9_tpo_sessions ADD COLUMN poc_migration TEXT;
ALTER TABLE v9_tpo_sessions ADD COLUMN hvn_zones TEXT;
ALTER TABLE v9_tpo_sessions ADD COLUMN lvn_zones TEXT;
ALTER TABLE v9_tpo_sessions ADD COLUMN volume_cluster TEXT;
ALTER TABLE v9_tpo_sessions ADD COLUMN previous_poc TEXT;
ALTER TABLE v9_tpo_sessions ADD COLUMN poc_stuck_since TEXT;
