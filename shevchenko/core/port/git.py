from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable, Literal, Union

from pydantic import BaseModel

from shevchenko.core.values import ContainerArtifact


class GitFetchError(RuntimeError):
    pass


class GitSource(BaseModel):
    """Build from a remote git repo. Commit is discovered at fetch time."""
    model_config = {"frozen": True}

    kind: Literal["git"] = "git"
    repo_url: str
    subdir: Path | None = None
    ref: str | None = None  # branch/tag/sha; None -> default branch
    dockerfile: str = "Dockerfile"  # relative to subdir


class PrebuiltSource(BaseModel):
    """Adopt an image someone already built and pushed."""
    model_config = {"frozen": True}

    kind: Literal["prebuilt"] = "prebuilt"
    image: str  # "user/repo:tag"


JobSource = Union[GitSource, PrebuiltSource]


# Field(discriminator="kind") when embedding in a parent model.


@dataclass(frozen=True)
class FetchedSource:
    """Outcome of materializing a git source.

    `commit` is *discovered* from HEAD — never supplied by the caller.
    """
    context_dir: Path  # build context on disk (repo root or subdir)
    commit: str  # full 40-char sha actually checked out
    sparse: bool  # whether only a subtree was materialized


@runtime_checkable
class SourceFetcher(Protocol):
    """Port: materialize a GitSource locally and report its commit."""

    def fetch(self, source: GitSource) -> FetchedSource: ...


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
class RemoteRefResolver(Protocol):
    """Port: resolve a ref to a commit sha without cloning."""
    def resolve(self, repo_url: str, ref: str | None = None) -> str | None: ...
