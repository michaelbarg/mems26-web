"""Tick Reversal observer — DB model for per-bar journal entries.

Uses the shared v9_system_signals table (system_id=3).
No separate table needed — the payload JSON stores the full analysis.
"""
