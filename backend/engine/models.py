"""
backend/engine/models.py
=========================
Data models — MarketData ו-SignalResult.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Bar:
    o: float; h: float; l: float; c: float
    v: float; bv: float; av: float; delta: float

@dataclass
class Features:
    cvd_trend:   str   = "NEUTRAL"
    effort:      str   = "NORMAL"
    rev15:       str   = "NONE"
    rev22:       str   = "NONE"
    rev15_price: float = 0.0
    rev22_price: float = 0.0
    ib_high:     float = 0.0
    ib_low:      float = 0.0
    ib_locked:   bool  = False
    poc_today:   float = 0.0
    poc_yest:    float = 0.0

@dataclass
class MarketData:
    ts:            int
    price:         float
    session_phase: str
    ses_min:       int
    ses_high:      float
    ses_low:       float
    bar:           Bar
    cvd_total:     float
    cvd_d20:       float
    woodi_pp:      float
    woodi_r1:      float
    woodi_r2:      float
    woodi_s1:      float
    woodi_s2:      float
    h72:           float
    l72:           float
    hwk:           float
    lwk:           float
    features:      Features

    @classmethod
    def from_dict(cls, d: dict) -> "MarketData":
        bar_d = d.get("bar", {})
        ses_d = d.get("session", {})
        cvd_d = d.get("cvd", {})
        woo_d = d.get("woodi", {})
        lev_d = d.get("levels", {})
        fea_d = d.get("features", {})

        bar = Bar(
            o=bar_d.get("o", 0), h=bar_d.get("h", 0),
            l=bar_d.get("l", 0), c=bar_d.get("c", 0),
            v=bar_d.get("v", 0), bv=bar_d.get("bv", 0),
            av=bar_d.get("av", 0), delta=bar_d.get("delta", 0),
        )
        features = Features(
            cvd_trend   = fea_d.get("cvd_trend", "NEUTRAL"),
            effort      = fea_d.get("effort",    "NORMAL"),
            rev15       = fea_d.get("rev15",     "NONE"),
            rev22       = fea_d.get("rev22",     "NONE"),
            rev15_price = fea_d.get("rev15_price", 0.0),
            rev22_price = fea_d.get("rev22_price", 0.0),
            ib_high     = fea_d.get("ib_high",   0.0),
            ib_low      = fea_d.get("ib_low",    0.0),
            ib_locked   = fea_d.get("ib_locked", False),
            poc_today   = fea_d.get("poc_today", 0.0),
            poc_yest    = fea_d.get("poc_yest",  0.0),
        )
        return cls(
            ts            = d.get("ts", 0),
            price         = bar.c,
            session_phase = ses_d.get("phase", "OVERNIGHT"),
            ses_min       = ses_d.get("min",   -1),
            ses_high      = ses_d.get("sh",    0.0),
            ses_low       = ses_d.get("sl",    0.0),
            bar           = bar,
            cvd_total     = cvd_d.get("total", 0.0),
            cvd_d20       = cvd_d.get("d20",   0.0),
            woodi_pp      = woo_d.get("pp",    0.0),
            woodi_r1      = woo_d.get("r1",    0.0),
            woodi_r2      = woo_d.get("r2",    0.0),
            woodi_s1      = woo_d.get("s1",    0.0),
            woodi_s2      = woo_d.get("s2",    0.0),
            h72           = lev_d.get("h72",   0.0),
            l72           = lev_d.get("l72",   0.0),
            hwk           = lev_d.get("hwk",   0.0),
            lwk           = lev_d.get("lwk",   0.0),
            features      = features,
        )


@dataclass
class SignalResult:
    direction:  str
    score:      int
    confidence: str
    entry:      float
    stop:       float
    target1:    float
    target2:    float
    target3:    float
    risk_pts:   float
    rationale:  str
    tl_color:   str
    ts:         int

    def to_dict(self) -> dict:
        return asdict(self)
