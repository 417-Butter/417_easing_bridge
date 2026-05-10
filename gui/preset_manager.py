import json
import os

DEFAULT_PRESETS = {
    "Linear": [[0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0]],
    "Ease In (Quad)": [[0.0, 0.0, 0.11, 0.0, 0.5, 0.0, 1.0, 1.0]],
    "Ease Out (Quad)": [[0.0, 0.0, 0.5, 1.0, 0.89, 1.0, 1.0, 1.0]],
    "Ease In Out (Quad)": [[0.0, 0.0, 0.45, 0.0, 0.55, 1.0, 1.0, 1.0]],
    "Ease In Out (Back)": [[0.0, 0.0, 0.68, -0.6, 0.32, 1.6, 1.0, 1.0]],
    "Bounce": [
        [0.0, 0.0, 0.1, 0.0, 0.4, 1.0, 0.5, 1.0],
        [0.5, 1.0, 0.6, 1.0, 0.6, 0.7, 0.7, 0.7],
        [0.7, 0.7, 0.8, 0.7, 0.8, 1.0, 0.85, 1.0],
        [0.85, 1.0, 0.9, 1.0, 0.9, 0.9, 0.95, 0.9],
        [0.95, 0.9, 1.0, 0.9, 1.0, 1.0, 1.0, 1.0]
    ]
}

DEFAULT_ORDER = list(DEFAULT_PRESETS.keys())

def get_default_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets.json")

class PresetManager:
    def __init__(self, filepath=None):
        self.filepath = filepath if filepath else get_default_path()
        self.custom_presets = {}
        self.order = []
        self.load_presets()

    def load_presets(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict) and 'presets' in data:
                    self.custom_presets = data['presets']
                    self.order = data.get('order', [])
                elif isinstance(data, dict):
                    self.custom_presets = data
                    self.order = []
            except Exception:
                self.custom_presets = {}
                self.order = []

    def save_presets(self):
        try:
            tmp = self.filepath + ".tmp"
            data = {'presets': self.custom_presets, 'order': self.order}
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            # Atomic rename to prevent corruption on crash
            if os.path.exists(self.filepath):
                os.replace(tmp, self.filepath)
            else:
                os.rename(tmp, self.filepath)
        except Exception as e:
            print(f"Failed to save presets: {e}")

    def get_all_presets(self):
        all_presets = {}
        all_names = list(DEFAULT_PRESETS.keys()) + list(self.custom_presets.keys())
        if self.order:
            for name in self.order:
                if name in DEFAULT_PRESETS:
                    all_presets[name] = DEFAULT_PRESETS[name]
                elif name in self.custom_presets:
                    all_presets[name] = self.custom_presets[name]
            for name in all_names:
                if name not in all_presets:
                    if name in DEFAULT_PRESETS:
                        all_presets[name] = DEFAULT_PRESETS[name]
                    elif name in self.custom_presets:
                        all_presets[name] = self.custom_presets[name]
        else:
            for name in DEFAULT_PRESETS:
                all_presets[name] = DEFAULT_PRESETS[name]
            for name in self.custom_presets:
                all_presets[name] = self.custom_presets[name]
        return all_presets

    def save_order(self, ordered_names):
        self.order = list(ordered_names)
        self.save_presets()

    def add_custom_preset(self, name, preset_data):
        self.custom_presets[name] = preset_data
        if name not in self.order:
            self.order.append(name)
        self.save_presets()
        
    def remove_custom_preset(self, name):
        if name in self.custom_presets:
            del self.custom_presets[name]
        if name in self.order:
            self.order.remove(name)
        self.save_presets()

    # ── Import / Export ───────────────────────

    def export_presets(self, filepath):
        """Export all presets (default + custom) to a file."""
        all_p = self.get_all_presets()
        data = {'presets': dict(all_p), 'order': list(all_p.keys())}
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def import_presets(self, filepath, overwrite=False):
        """Import presets from a file.
        overwrite=True: replace all custom presets.
        overwrite=False: add only new presets (skip duplicates).
        Returns (added_count, skipped_count).
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict) and 'presets' in data:
            incoming = data['presets']
        elif isinstance(data, dict):
            incoming = data
        else:
            raise ValueError("Invalid preset file format")

        if overwrite:
            self.custom_presets = {}
            self.order = []

        added = 0
        skipped = 0
        existing = set(DEFAULT_PRESETS.keys()) | set(self.custom_presets.keys())
        for name, preset_data in incoming.items():
            if name in DEFAULT_PRESETS:
                skipped += 1
                continue
            if not overwrite and name in existing:
                skipped += 1
                continue
            self.custom_presets[name] = preset_data
            if name not in self.order:
                self.order.append(name)
            added += 1

        self.save_presets()
        return added, skipped
