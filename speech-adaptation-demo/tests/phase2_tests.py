import os

from phase2.continual_learning import CorrectionManager
from phase2.pronunciation_engine import PronunciationMapper
from phase2.profile_manager import ProfileManager
from phase2.advanced_metrics import calculate_semscore, meaning_error_rate
from phase2.adaptive_interaction import AdaptiveInteractionManager
from phase2.db import init_db


def test_profile_create_load():
    init_db()
    pm = ProfileManager()
    user_id = pm.create_profile("Test User", {"condition": "none"})
    profile = pm.load_profile(user_id)
    assert profile["user_id"] == user_id


def test_correction_flow():
    cm = CorrectionManager()
    pm = ProfileManager()
    user_id = pm.create_profile("Correct User", {})
    cm.add_correction(user_id, "audio.wav", "hello", "helo", "hello", "test")
    history = cm.get_correction_history(user_id, limit=5)
    assert len(history) >= 1


def test_pronunciation_mapper():
    mapper = PronunciationMapper()
    pairs = mapper.detect_pattern("cal gary", "calgary")
    assert isinstance(pairs, list)


def test_advanced_metrics():
    s = calculate_semscore("turn on the lights", "turn on lights")
    assert s >= 0.0
    mer = meaning_error_rate("turn on the lights", "turn on lights")
    assert mer >= 0.0


def test_adaptive_interaction():
    manager = AdaptiveInteractionManager()
    result = manager.detect_frustration({"repeated_corrections": 3})
    assert "score" in result
