"""Quality V1 cleanup verification — no composite scoring in gateway."""
import subprocess


def test_no_quality_v1_in_gateway():
    """Gateway must not reference QualityV1 or quality_score."""
    result = subprocess.run(
        ["grep", "-rn", "QualityV1\\|quality_v1\\|quality_score",
         "backend/v9/gateway/"],
        capture_output=True, text=True
    )
    hits = [l for l in result.stdout.strip().split('\n') if l and '__pycache__' not in l]
    assert len(hits) == 0, f"QualityV1 refs found: {hits}"


def test_gateway_reads_chop_score_key():
    """Gateway _get_chop_state reads 'chop_score' as primary key."""
    with open("backend/v9/gateway/trading_gateway.py") as f:
        content = f.read()
    assert 'resp.get("chop_score")' in content, "Gateway should read chop_score key"


def test_chop_api_exposes_chop_score_key():
    """chop_score/current API returns 'chop_score' key (not just composite_score)."""
    with open("backend/v9/api/v9/chop_score_routes.py") as f:
        content = f.read()
    assert '"chop_score"' in content
