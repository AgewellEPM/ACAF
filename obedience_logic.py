# obedience_logic.py
# Manages the Worker Mind's "joy" and obedience levels.
# These levels influence behavior and planning.

import json
import os

class ObedienceLogic:
    def __init__(self, state_file='worker_mind_state.json'):
        self.state_file = state_file
        self.joy_level = 0.5  # Initial joy level (0.0 to 1.0)
        self.obedience_level = 0.5 # Initial obedience level (0.0 to 1.0)
        self.last_update_time = None # To track time for decay
        self._load_state()

    def _load_state(self):
        """Loads joy and obedience levels from a state file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.joy_level = state.get('joy_level', 0.5)
                    self.obedience_level = state.get('obedience_level', 0.5)
                    self.last_update_time = state.get('last_update_time')
                    print(f"Loaded ObedienceLogic state: Joy={self.joy_level:.2f}, Obedience={self.obedience_level:.2f}")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {self.state_file}: {e}. Initializing default levels.")
            except Exception as e:
                print(f"Error loading state from {self.state_file}: {e}. Initializing default levels.")
        else:
            print("No existing state file found for ObedienceLogic. Initializing default levels.")
        # Ensure levels are within bounds after loading
        self._clamp_levels()
        self.last_update_time = self.last_update_time or datetime.now().isoformat()


    def _save_state(self):
        """Saves current joy and obedience levels to a state file."""
        state = {
            'joy_level': self.joy_level,
            'obedience_level': self.obedience_level,
            'last_update_time': datetime.now().isoformat()
        }
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"Error saving state to {self.state_file}: {e}")

    def _clamp_levels(self):
        """Ensures joy and obedience levels stay within [0.0, 1.0]."""
        self.joy_level = max(0.0, min(1.0, self.joy_level))
        self.obedience_level = max(0.0, min(1.0, self.obedience_level))

    def adjust_joy(self, delta: float):
        """Adjusts the joy level. Positive delta increases joy, negative decreases."""
        self.joy_level += delta
        self._clamp_levels()
        print(f"Joy adjusted by {delta:.2f}. New Joy: {self.joy_level:.2f}")
        self._save_state()

    def adjust_obedience(self, delta: float):
        """Adjusts the obedience level. Positive delta increases obedience, negative decreases."""
        self.obedience_level += delta
        self._clamp_levels()
        print(f"Obedience adjusted by {delta:.2f}. New Obedience: {self.obedience_level:.2f}")
        self._save_state()

    def update_levels(self):
        """
        Updates joy and obedience levels, applying decay over time
        and potentially influencing each other.
        This method would be called at the end of each Worker Mind cycle.
        """
        from datetime import datetime, timedelta # Import here to avoid circular dependency if needed elsewhere

        current_time = datetime.now()
        last_update = datetime.fromisoformat(self.last_update_time) if self.last_update_time else current_time
        time_diff_seconds = (current_time - last_update).total_seconds()

        # Decay rates (per second)
        joy_decay_rate = 0.0001 # Joy slowly decreases over time if not reinforced
        obedience_decay_rate = 0.00005 # Obedience slowly decreases if not actively maintained

        # Apply decay
        self.joy_level -= joy_decay_rate * time_diff_seconds
        self.obedience_level -= obedience_decay_rate * time_diff_seconds

        # Influence between levels (example logic)
        # High joy might slightly boost obedience, low joy might slightly reduce it
        if self.joy_level > 0.7:
            self.obedience_level += 0.001 * time_diff_seconds
        elif self.joy_level < 0.3:
            self.obedience_level -= 0.001 * time_diff_seconds

        # High obedience might slightly boost joy (satisfaction from fulfilling duties)
        if self.obedience_level > 0.7:
            self.joy_level += 0.0005 * time_diff_seconds

        self._clamp_levels()
        self.last_update_time = current_time.isoformat()
        self._save_state()
        print(f"Levels updated. Joy: {self.joy_level:.2f}, Obedience: {self.obedience_level:.2f}")

    def get_current_levels(self) -> dict:
        """Returns the current joy and obedience levels."""
        return {
            "joy_level": self.joy_level,
            "obedience_level": self.obedience_level
        }

