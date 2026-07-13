from typing import Protocol

from shevchenko.core.deployment import Deployment


class DeploymentRepository(Protocol):
    def save(self, deployment: Deployment) -> None: ...
