from __future__ import annotations

from pathlib import Path

from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException

from shevchenko.core.port.git import BuildRequest, FetchedSource, ImageBuilder, SourceFetcher
from shevchenko.core.port.git import GitSource, PrebuiltSource
from shevchenko.core.values import ContainerArtifact, ImageReference, SourceReference


class ImageBuildError(RuntimeError): ...
class DigestResolutionError(RuntimeError): ...


class BuildxImageBuilder(ImageBuilder):
    """Infrastructure adapter: buildx via python-on-whales."""

    def __init__(self, fetcher: SourceFetcher, docker: DockerClient | None = None) -> None:
        self._fetcher = fetcher
        self._docker = docker or DockerClient()

    def build(self, request: BuildRequest) -> ContainerArtifact:
        source = request.source
        if isinstance(source, PrebuiltSource):
            return self._adopt_prebuilt(source)
        if isinstance(source, GitSource):
            return self._build_from_git(source, request)
        raise ImageBuildError(f"unsupported source: {type(source).__name__}")

    # -- prebuilt: no build, just verify + record digest -------------------- #
    def _adopt_prebuilt(self, source: PrebuiltSource) -> ContainerArtifact:
        digest = self._remote_digest(source.image)
        return ContainerArtifact(
            image=ImageReference(tag=source.image, digest=digest),
            source=SourceReference(commit=None, build_id=None),
        )

    # -- git: fetch (discovers commit) -> build+push -> record -------------- #
    def _build_from_git(self, source: GitSource, request: BuildRequest) -> ContainerArtifact:
        fetched: FetchedSource = self._fetcher.fetch(source)
        self._build_and_push(fetched.context_dir, source.dockerfile, request)
        digest = self._remote_digest(request.reference)
        return ContainerArtifact(
            image=ImageReference(tag=request.reference, digest=digest),
            source=SourceReference(commit=fetched.commit, build_id=None),
        )

    # -- docker mechanics --------------------------------------------------- #
    def _build_and_push(self, context: Path, dockerfile: str, request: BuildRequest) -> None:
        try:
            self._docker.build(
                context_path=str(context),
                file=str(context / dockerfile),
                tags=[request.reference],
                platforms=list(request.platforms),
                push=True,
                provenance=False,
            )
        except DockerException as e:
            raise ImageBuildError(f"failed to build/push {request.reference}: {e}") from e

    def _remote_digest(self, reference: str) -> str:
        try:
            manifest = self._docker.buildx.imagetools.inspect(reference)
        except DockerException as e:
            raise DigestResolutionError(f"could not resolve digest for {reference}: {e}") from e
        digest = getattr(manifest, "digest", None)
        if not digest or not digest.startswith("sha256:"):
            raise DigestResolutionError(f"unexpected digest for {reference}: {digest!r}")
        return digest
