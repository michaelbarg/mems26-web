"""DB model: Woodies Trade Terminal States (PROMPT 4 · 4.1).

Records every terminal state emission from the Woodies decision tree.
18 distinct terminal states per Decision Tree V1 § Section 6.
"""

from sqlalchemy import Column, String, Float, DateTime, Text
from sqlalchemy.sql import func

from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class WoodiesTradeTerminal(Base):
    __tablename__ = "woodies_trade_terminals"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    trade_id = Column(String(40), nullable=False, index=True)
    terminal_state = Column(String(40), nullable=False, index=True)
    phase = Column(String(10), nullable=False)  # "entry" | "active"
    priority_class = Column(String(20))
    triggered_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    bar_context = Column(JsonColumn, nullable=False, default=dict)
    stage_id = Column(String(40), nullable=False)
    direction = Column(String(10))
    entry_price = Column(Float)
    exit_price = Column(Float)
    pnl_points = Column(Float)
    classification = Column(String(20))  # REACTIVE | INITIATIVE | NULL
    notes = Column(Text)
