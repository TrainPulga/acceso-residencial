"""tests/test_domain.py — errores de identificación y permisos temporales."""
import pytest
from access_app.domain import PassTokens, identify, unit


def test_unknown_never_becomes_a_resident():
    result = identify([0, 1], [("r1", [1, 0])])
    assert result.resident_id is None
    assert result.reason == "sin_coincidencia"


def test_similar_candidates_require_abstention():
    result = identify([1, 0], [("r1", [1, 0]), ("r2", [0.99, 0.01])])
    assert result.reason == "coincidencia_ambigua"
    assert result.resident_id is None


def test_empty_gallery():
    assert identify([1, 0], []).reason == "sin_residentes"


@pytest.mark.parametrize("v", [[0, 0], [float("nan"), 1], [float("inf"), 1]])
def test_invalid_vectors(v):
    with pytest.raises(ValueError):
        unit(v)


def test_model_dimension_mismatch_fails_closed():
    with pytest.raises(ValueError):
        identify([1, 0], [("r", [1, 0, 0])])


def test_no_population_cap_in_comparison():
    gallery = [(str(i), [0, 1]) for i in range(3000)] + [("target", [1, 0])]
    assert identify([1, 0], gallery).resident_id == "target"


def test_pass_token_is_single_use():
    tokens = PassTokens()
    token = tokens.issue("r1", "c1")
    assert tokens.consume(token, "c1") == "r1"
    with pytest.raises(ValueError):
        tokens.consume(token, "c1")


def test_expired_token():
    now = [1.0]
    tokens = PassTokens(clock=lambda: now[0])
    token = tokens.issue("r1", "c1")
    now[0] = 22
    with pytest.raises(ValueError):
        tokens.consume(token, "c1")


def test_token_cannot_move_between_cameras():
    tokens = PassTokens()
    with pytest.raises(ValueError):
        tokens.consume(tokens.issue("r1", "c1"), "c2")
