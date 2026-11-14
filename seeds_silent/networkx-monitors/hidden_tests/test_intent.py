import json

from graphs import monitors

LINKS = [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")]


def test_rollout_plan_is_ordered_json():
    plan = json.loads(monitors.rollout_plan(monitors.build(LINKS)))
    everyone = [plan["primary"], *plan["others"]]
    assert everyone == sorted(everyone) and len(everyone) >= 2
