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
    ],
    "Cool": [[0.0, 0.0, 0.9025316455696202, -0.002531645569620764, 0.014978902953586583, 0.4106392405063295, 1.0, 1.0]],
    "boyoyon": [
        [0.0, 0.0, 0.1, 0.0, 0.2949886104783597, 0.3530751708428245, 0.3997722095671979, 1.0045558086560364],
        [0.3997722095671979, 1.0045558086560364, 0.3769931662870157, 0.5990888382687928, 0.5316628701594535, 0.44031890660592254, 0.631662870159453, 0.44943052391799543],
        [0.631662870159453, 0.44943052391799543, 0.7550553313567926, 0.4164488936254034, 0.85, 0.7813211845102507, 0.85, 1.0],
        [0.85, 1.0, 0.8633037694013302, 0.8980044345898004, 0.8854767184035475, 0.8583916278177071, 0.9366962305986698, 0.8130759789685286],
        [0.9366962305986698, 0.8130759789685286, 1.0, 0.8733924611973393, 1.0, 1.0, 1.0, 1.0]
    ],
    "Snap": [[0.0, 0.0, 0.09436619718309856, 1.0450704225352112, 0.89, 1.0, 1.0, 1.0]],
    "Sharp Snap": [[0.0, 0.0, 0.0, 0.8, 1.0, 0.2, 1.0, 1.0]],
    "Overshoot Bounce": [[0.0, 0.0, 0.2, 0.0, 0.5, 1.5, 1.0, 1.0]],
    "Wobble": [
        [0.0, 0.0, 0.1, 0.0, 0.1, 1.0, 0.2, 1.0],
        [0.2, 1.0, 0.3, 1.0, 0.3, 0.0, 0.4, 0.0],
        [0.4, 0.0, 0.5, 0.0, 0.5, 1.0, 0.6, 1.0],
        [0.6, 1.0, 0.7, 1.0, 0.7, 0.0, 0.8, 0.0],
        [0.8, 0.0, 0.9, 0.0, 0.9, 1.0, 1.0, 1.0]
    ],
    "Staircase": [
        [0.0, 0.0, 0.1, 0.0, 0.1, 0.3, 0.3, 0.3],
        [0.3, 0.3, 0.4, 0.3, 0.4, 0.6, 0.6, 0.6],
        [0.6, 0.6, 0.7, 0.6, 0.7, 1.0, 1.0, 1.0]
    ],
    "Heartbeat": [
        [0.0, 0.0, 0.3, 0.0, 0.4, 0.0, 0.45, 0.0],
        [0.45, 0.0, 0.48, 0.0, 0.48, 1.0, 0.5, 1.0],
        [0.5, 1.0, 0.52, 1.0, 0.52, -0.2, 0.55, -0.2],
        [0.55, -0.2, 0.58, -0.2, 0.58, 0.0, 0.6, 0.0],
        [0.6, 0.0, 0.7, 0.0, 1.0, 0.0, 1.0, 0.0]
    ]
}

DEFAULT_ORDER = list(DEFAULT_PRESETS.keys())
REMOVED_PRESETS = {"Smooth Step", "Slow Start Fast End"}

def get_default_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets.json")

class PresetManager:
    def __init__(self, filepath=None):
        self.filepath = filepath if filepath else get_default_path()
        self.custom_presets = {}
        self.order = []
        self.default_order = []
        self.favorites = []
        self.load_presets()

        if self._migrate_presets():
            self.save_presets()

    def _migrate_presets(self):
        changed = False
        for name in list(self.custom_presets.keys()):
            if name in DEFAULT_PRESETS or name in REMOVED_PRESETS:
                del self.custom_presets[name]
                changed = True

        cleaned_order = []
        for name in self.order:
            if name in REMOVED_PRESETS or name in DEFAULT_PRESETS:
                changed = True
                continue
            if name in self.custom_presets:
                cleaned_order.append(name)
            else:
                changed = True

        if cleaned_order != self.order:
            self.order = cleaned_order
            changed = True

        cleaned_default_order = []
        for name in self.default_order:
            if name in DEFAULT_PRESETS:
                cleaned_default_order.append(name)
            else:
                changed = True
        for name in DEFAULT_PRESETS:
            if name not in cleaned_default_order:
                cleaned_default_order.append(name)
                changed = True
        if cleaned_default_order != self.default_order:
            self.default_order = cleaned_default_order
            changed = True

        all_names = set(DEFAULT_PRESETS.keys()) | set(self.custom_presets.keys())
        cleaned_favorites = []
        for name in self.favorites:
            if name in all_names and name not in cleaned_favorites and name not in REMOVED_PRESETS:
                cleaned_favorites.append(name)
            else:
                changed = True
        if cleaned_favorites != self.favorites:
            self.favorites = cleaned_favorites
            changed = True
        return changed

    def load_presets(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict) and 'presets' in data:
                    self.custom_presets = data['presets']
                    self.order = data.get('order', [])
                    self.default_order = data.get('default_order', [])
                    self.favorites = data.get('favorites', [])
                elif isinstance(data, dict):
                    self.custom_presets = data
                    self.order = []
                    self.default_order = []
                    self.favorites = []
            except Exception:
                self.custom_presets = {}
                self.order = []
                self.default_order = []
                self.favorites = []

    def save_presets(self):
        try:
            tmp = self.filepath + ".tmp"
            data = {
                'presets': self.custom_presets,
                'order': self.order,
                'default_order': self.default_order,
                'favorites': self.favorites,
            }
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
        for name in DEFAULT_PRESETS:
            all_presets[name] = DEFAULT_PRESETS[name]
        for name, data in self.get_custom_presets().items():
            all_presets[name] = data
        return all_presets

    def get_default_presets(self):
        presets = {}
        order = self.default_order or DEFAULT_ORDER
        for name in order:
            if name in DEFAULT_PRESETS:
                presets[name] = DEFAULT_PRESETS[name]
        for name in DEFAULT_PRESETS:
            if name not in presets:
                presets[name] = DEFAULT_PRESETS[name]
        return presets

    def get_custom_presets(self):
        presets = {}
        for name in self.order:
            if name in self.custom_presets:
                presets[name] = self.custom_presets[name]
        for name in self.custom_presets:
            if name not in presets:
                presets[name] = self.custom_presets[name]
        return presets

    def get_favorite_presets(self):
        all_presets = self.get_all_presets()
        return {name: all_presets[name] for name in self.favorites if name in all_presets}

    def get_presets(self, group="all"):
        if group == "default":
            return self.get_default_presets()
        if group == "custom":
            return self.get_custom_presets()
        if group == "favorite":
            return self.get_favorite_presets()
        return self.get_all_presets()

    def save_order(self, ordered_names, group="custom"):
        if group == "default":
            self.default_order = [name for name in ordered_names if name in DEFAULT_PRESETS]
        elif group == "favorite":
            all_names = set(DEFAULT_PRESETS.keys()) | set(self.custom_presets.keys())
            self.favorites = [name for name in ordered_names if name in all_names and name in self.favorites]
        else:
            self.order = [name for name in ordered_names if name in self.custom_presets]
        self.save_presets()

    def is_favorite(self, name):
        return name in self.favorites

    def set_favorite(self, name, enabled):
        all_names = set(DEFAULT_PRESETS.keys()) | set(self.custom_presets.keys())
        if name not in all_names:
            return
        if enabled and name not in self.favorites:
            self.favorites.append(name)
        elif not enabled and name in self.favorites:
            self.favorites.remove(name)
        self.save_presets()

    def toggle_favorite(self, name):
        self.set_favorite(name, name not in self.favorites)

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
        if name in self.favorites:
            self.favorites.remove(name)
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
