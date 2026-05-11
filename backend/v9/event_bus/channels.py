"""Event Bus channel definitions — single source of truth for stream keys."""

# Redis Streams keys for the Event Bus.
# Convention: mems26:events:<domain>.<event>

# Price
CH_PRICE_TICK = "mems26:events:price.tick"
CH_PRICE_SNAPSHOT = "mems26:events:price.snapshot"

# Bars
CH_BAR_5MIN = "mems26:events:bar.5min"
CH_BAR_TICK_REVERSAL = "mems26:events:bar.tick_reversal"

# Signals
CH_SIGNAL_FIRED = "mems26:events:signal.fired"

# System health
CH_SYSTEM_HEALTH = "mems26:events:system.health"

# All channels for introspection
ALL_CHANNELS = [
    CH_PRICE_TICK,
    CH_PRICE_SNAPSHOT,
    CH_BAR_5MIN,
    CH_BAR_TICK_REVERSAL,
    CH_SIGNAL_FIRED,
    CH_SYSTEM_HEALTH,
]
