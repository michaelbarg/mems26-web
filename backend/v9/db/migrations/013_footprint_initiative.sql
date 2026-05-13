-- P-FP-2.1: Initiative/Reactive columns
ALTER TABLE v9_footprint_journal ADD COLUMN initiative_type TEXT;
ALTER TABLE v9_footprint_journal ADD COLUMN reactive_flag INTEGER DEFAULT 0;
ALTER TABLE v9_footprint_journal ADD COLUMN combined_class TEXT;
