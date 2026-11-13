from types import SimpleNamespace

from geodesync.ui.app import GeodeSyncApp


class SearchValue:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeButton:
    def __init__(self, label):
        self.text = label
        self.visible = True
        self.options = {}

    def grid(self, **kwargs):
        self.visible = True

    def grid_remove(self):
        self.visible = False

    def config(self, **kwargs):
        self.options.update(kwargs)


class FakeLabel:
    def __init__(self):
        self.visible = True

    def grid(self):
        self.visible = True

    def grid_remove(self):
        self.visible = False


def make_app(query=""):
    texture = FakeButton("Texture Packs")
    mod_manager = FakeButton("Mod Manager")
    save_doctor = FakeButton("Save Doctor")
    cache_cleaner = FakeButton("Cache Cleaner")
    mods_label = FakeLabel()
    repair_label = FakeLabel()
    app = SimpleNamespace(
        tool_search_var=SearchValue(query),
        tool_buttons=[
            (texture, "Texture Packs", "#10b981", "#19221d", 0, 1),
            (mod_manager, "Mod Manager", "#10b981", "#19221d", 0, 2),
            (save_doctor, "Save Doctor", "#a855f7", "#262015", 2, 1),
            (cache_cleaner, "Cache Cleaner", "#8b949e", "#262015", 2, 2),
        ],
        tool_group_labels=[(0, "MODS", mods_label), (2, "REPAIR", repair_label)],
    )
    return app, texture, mod_manager, save_doctor, cache_cleaner, mods_label, repair_label


def test_tool_search_filters_buttons_and_hides_empty_categories():
    app, texture, mod_manager, save_doctor, cache_cleaner, mods_label, repair_label = make_app("texture")

    GeodeSyncApp._filter_tools(app)

    assert texture.visible
    assert not mod_manager.visible
    assert not save_doctor.visible
    assert not cache_cleaner.visible
    assert mods_label.visible
    assert not repair_label.visible


def test_tool_search_by_category_shows_that_categories_actions():
    app, texture, mod_manager, save_doctor, cache_cleaner, mods_label, repair_label = make_app("repair")

    GeodeSyncApp._filter_tools(app)

    assert not texture.visible
    assert not mod_manager.visible
    assert save_doctor.visible
    assert cache_cleaner.visible
    assert not mods_label.visible
    assert repair_label.visible


def test_clearing_tool_search_restores_all_actions():
    app, texture, mod_manager, save_doctor, cache_cleaner, mods_label, repair_label = make_app("")

    GeodeSyncApp._filter_tools(app)

    assert all(button.visible for button in (texture, mod_manager, save_doctor, cache_cleaner))
    assert mods_label.visible and repair_label.visible
