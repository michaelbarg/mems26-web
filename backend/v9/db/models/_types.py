"""Shared column types — cross-database compatibility."""

from sqlalchemy import JSON, Integer, BigInteger
from sqlalchemy.dialects.postgresql import JSONB

# Use JSONB on PostgreSQL, plain JSON elsewhere (SQLite tests)
JsonColumn = JSON().with_variant(JSONB(), "postgresql")

# Use BigInteger on PostgreSQL, Integer on SQLite (for autoincrement)
BigIntPK = Integer().with_variant(BigInteger(), "postgresql")
