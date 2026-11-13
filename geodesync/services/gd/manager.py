"""GDManager: facade composing the domain mixins (v2.8.0 behaviour, split by domain)."""


from geodesync.core.config import DEFAULT_MANIFEST, DEFAULT_TARGET_GD
from geodesync.services.gd.steam import SteamMixin
from geodesync.services.gd.game import GameMixin
from geodesync.services.gd.mods import ModsMixin
from geodesync.services.gd.assets import AssetsMixin
from geodesync.services.gd.saves import SavesMixin
from geodesync.services.gd.demonlist import DemonlistMixin



class GDManager(SteamMixin, GameMixin, ModsMixin, AssetsMixin, SavesMixin, DemonlistMixin):
    """Facade over the domain mixins; the UI talks to this one object."""

    def __init__(self):
        self.steam_path = self.detect_steam_path()
        self.custom_save_path = None
        self.gd_path = self.detect_gd_path()
        self.manifest_path = self.get_manifest_path()
        self.target_manifest = DEFAULT_MANIFEST
        self.target_gd_version = DEFAULT_TARGET_GD
