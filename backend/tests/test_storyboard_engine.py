from app.domain.storyboard import CameraAngle, ShotType
from app.services.storyboard_engine import StoryboardEngine, StoryboardGenerationError, StoryboardRequest


def test_generate_storyboard_from_plain_script_is_deterministic() -> None:
    request = StoryboardRequest("A quiet street at night. A man walks toward the old house.", "p1", "cinematic", 8)
    first = StoryboardEngine().generate(request)
    second = StoryboardEngine().generate(request)
    assert first.storyboard_id == second.storyboard_id
    assert first.scenes[0].shots[0].duration_seconds == 4
    assert first.validate() == ()


def test_planner_output_is_validated_and_normalized() -> None:
    def planner(script, context):
        return [{
            "setting": "INT. studio",
            "characters": ("host",),
            "action": "Host explains the topic.",
            "shots": [{
                "prompt": "host speaking to camera",
                "duration_seconds": 5,
                "shot_type": "close-up",
                "camera_angle": "low",
            }],
        }]

    storyboard = StoryboardEngine(planner).generate(StoryboardRequest("hello", "p2", "news", 5))
    shot = storyboard.scenes[0].shots[0]
    assert shot.shot_type is ShotType.CLOSE_UP
    assert shot.camera_angle is CameraAngle.LOW
    assert shot.character_ids == ("host",)


def test_invalid_duration_fails_explicitly() -> None:
    def planner(script, context):
        return [{"setting": "room", "action": "x", "shots": [{"prompt": "x", "duration_seconds": 20}]}]

    try:
        StoryboardEngine(planner).generate(StoryboardRequest("hello", "p3"))
    except ValueError as exc:
        assert "between 2 and 10" in str(exc)
    else:
        raise AssertionError("invalid shot duration must fail")


def test_scene_can_be_regenerated_without_changing_other_scenes() -> None:
    engine = StoryboardEngine()
    storyboard = engine.generate(StoryboardRequest("SCENE one\nA person enters.\nSCENE two\nA door closes.", "p4"))
    old_second = storyboard.scenes[1]
    updated = engine.regenerate_scene(storyboard, storyboard.scenes[0].scene_id, {"setting": "new room", "action": "A person sits.", "shots": [{"prompt": "person sitting", "duration_seconds": 3}]})
    assert updated.scenes[0].setting == "new room"
    assert updated.scenes[1] == old_second


def test_empty_script_is_rejected() -> None:
    try:
        StoryboardEngine().generate(StoryboardRequest("  ", "p5"))
    except StoryboardGenerationError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("empty script must fail")
