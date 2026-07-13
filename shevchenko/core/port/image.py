from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from shevchenko.core.port.git import JobSource
from shevchenko.core.values import ContainerArtifact


class ImageName(str):
    """The repository name an image should be published under."""


@dataclass(frozen=True)
class BuildRequest:
    """A domain intent: turn this source into a published image."""
    source: JobSource
    image_name: str
    tag: str = "latest"
    platforms: tuple[str, ...] = ("linux/amd64",)

    @property
    def reference(self) -> str:
        return f"{self.image_name}:{self.tag}"


@runtime_checkable
class ImageBuilder(Protocol):
    """Port: produce a ContainerArtifact from a build request."""
    def build(self, request: BuildRequest) -> ContainerArtifact: ...


@dataclass(frozen=True)
class FetchedSource:
    context_dir: Path
    commit: str


@runtime_checkable
class SourceFetcher(Protocol):
    """Port: materialize a git source locally and report its commit."""
    def fetch(self, source: "GitSourceLike") -> FetchedSource: ...


class GitSourceLike(Protocol):
    repo_url: str
    ref: str | None
    subdir: object | None
