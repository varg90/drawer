import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.focus_tracker import FocusTrackerState


def make_tracker(saved_apps=None, enabled=False, slot_index=0):
    return FocusTrackerState(
        saved_apps=saved_apps or [None] * 5,
        enabled=enabled,
        slot_index=slot_index,
    )


def test_default_state():
    state = make_tracker()
    assert state.enabled is False
    assert state.slot_index == 0
    assert state.saved_apps == [None, None, None, None, None]
    assert state.current_app is None


def test_toggle_enabled():
    state = make_tracker()
    state.enabled = True
    assert state.enabled is True


def test_set_app_in_slot():
    state = make_tracker()
    state.set_app(0, "Photoshop")
    assert state.saved_apps[0] == "Photoshop"
    assert state.current_app == "Photoshop"


def test_clear_slot():
    state = make_tracker(saved_apps=["Photoshop", None, None, None, None])
    state.clear_slot(0)
    assert state.saved_apps[0] is None
    assert state.current_app is None


def test_next_slot_wraps():
    state = make_tracker(slot_index=4)
    state.next_slot()
    assert state.slot_index == 0


def test_prev_slot_wraps():
    state = make_tracker(slot_index=0)
    state.prev_slot()
    assert state.slot_index == 4


def test_cycle_through_all_slots():
    state = make_tracker(
        saved_apps=["Photoshop", "Krita", None, None, "Blender"],
        slot_index=0,
    )
    order = [state.current_app]
    for _ in range(4):
        state.next_slot()
        order.append(state.current_app)
    assert order == ["Photoshop", "Krita", None, None, "Blender"]


def test_save_state():
    state = make_tracker(
        saved_apps=["Photoshop", None, "Krita", None, None],
        enabled=True,
        slot_index=2,
    )
    data = state.save_state()
    assert data == {
        "focus_enabled": True,
        "focus_slot": 2,
        "focus_apps": ["Photoshop", None, "Krita", None, None],
    }


def test_restore_state():
    state = make_tracker()
    state.restore_state({
        "focus_enabled": True,
        "focus_slot": 1,
        "focus_apps": ["PS", "Krita", None, None, None],
    })
    assert state.enabled is True
    assert state.slot_index == 1
    assert state.current_app == "Krita"


def test_restore_state_missing_keys():
    state = make_tracker()
    state.restore_state({})
    assert state.enabled is False
    assert state.slot_index == 0
    assert state.saved_apps == [None] * 5


def test_slot_count_fixed_at_five():
    state = make_tracker()
    assert len(state.saved_apps) == 5


def test_restore_state_truncates_long_list():
    state = make_tracker()
    state.restore_state({
        "focus_apps": ["A", "B", "C", "D", "E", "F", "G"],
    })
    assert len(state.saved_apps) == 5
    assert state.saved_apps == ["A", "B", "C", "D", "E"]


def test_restore_state_pads_short_list():
    state = make_tracker()
    state.restore_state({
        "focus_apps": ["A", "B"],
    })
    assert len(state.saved_apps) == 5
    assert state.saved_apps == ["A", "B", None, None, None]
