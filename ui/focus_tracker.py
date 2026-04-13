"""Focus-aware pause: toggle + cycling app selector widget."""

NUM_SLOTS = 5


class FocusTrackerState:
    """Pure logic for focus tracker — no Qt dependency, easy to test."""

    def __init__(self, saved_apps=None, enabled=False, slot_index=0):
        self.enabled = enabled
        self.slot_index = slot_index
        if saved_apps is None:
            self.saved_apps = [None] * NUM_SLOTS
        else:
            self.saved_apps = list(saved_apps)

    @property
    def current_app(self):
        return self.saved_apps[self.slot_index]

    def set_app(self, slot, name):
        self.saved_apps[slot] = name

    def clear_slot(self, slot):
        self.saved_apps[slot] = None

    def next_slot(self):
        self.slot_index = (self.slot_index + 1) % NUM_SLOTS

    def prev_slot(self):
        self.slot_index = (self.slot_index - 1) % NUM_SLOTS

    def save_state(self):
        return {
            "focus_enabled": self.enabled,
            "focus_slot": self.slot_index,
            "focus_apps": list(self.saved_apps),
        }

    def restore_state(self, data):
        self.enabled = data.get("focus_enabled", False)
        self.slot_index = data.get("focus_slot", 0)
        apps = data.get("focus_apps", [None] * NUM_SLOTS)
        # Normalize to exactly NUM_SLOTS entries
        apps = list(apps[:NUM_SLOTS])
        while len(apps) < NUM_SLOTS:
            apps.append(None)
        self.saved_apps = apps
        self.slot_index = min(self.slot_index, NUM_SLOTS - 1)
