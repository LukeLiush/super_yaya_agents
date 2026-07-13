from shevchenko.contracts.plugins import BackendPlugin


class UnknownTechnology(Exception):
    pass


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, BackendPlugin] = {}  # starts empty

    def get(self, technology: str) -> BackendPlugin:
        if technology not in self._plugins:
            raise UnknownTechnology(technology)
        return self._plugins[technology]

    def register(self, plugin: BackendPlugin) -> None:
        # validation gate from earlier...
        self._plugins[plugin.technology] = plugin  # <-- the ONLY place it's populated
