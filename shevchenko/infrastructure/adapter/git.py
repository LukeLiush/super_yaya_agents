from __future__ import annotations

import shutil
from pathlib import Path

from dulwich import porcelain
from dulwich.repo import Repo

from shevchenko.core.port.git import FetchedSource, GitFetchError, SourceFetcher, GitSource, RemoteRefResolver


class DulwichGitFetcher(SourceFetcher):
    """Pure-Python git fetch (no git binary) — a SourceFetcher adapter.

    Monorepo optimizations:
      * shallow clone (depth=1) — skips history.
      * cone-mode sparse checkout — when the source has a subdir, only that
        subtree is materialized on disk, keeping the build context small.

    Limitation: Dulwich has no blobless partial clone (--filter=blob:none), so
    the full object set is still *downloaded*; sparse checkout only limits what
    is *written to disk*. For download-side savings on huge monorepos, provide a
    native-git SourceFetcher implementing the same port.
    """

    def __init__(self, workspace_root: Path, *, keep_clone: bool = False) -> None:
        self._root = workspace_root
        self._keep_clone = keep_clone  # False -> wipe dest before clone (reproducible)

    # -- port implementation ------------------------------------------------ #
    def fetch(self, source: GitSource) -> FetchedSource:
        subdir: str | None = str(source.subdir) if source.subdir else None
        use_sparse: bool = subdir is not None
        dest: Path = self._root / self._slug(source.repo_url)

        repo: Repo = self._clone(source.repo_url, dest, source.ref, defer_checkout=use_sparse)
        try:
            if use_sparse:
                self._sparse_materialize(repo, subdir)  # type: ignore[arg-type]
            self._ensure_ref(repo, source.ref)
            commit = repo.head().decode("ascii")
        finally:
            repo.close()

        context: Path = dest / subdir if subdir else dest
        self._assert_context_exists(context, subdir)
        return FetchedSource(context_dir=context, commit=commit, sparse=use_sparse)

    # -- clone -------------------------------------------------------------- #
    def _clone(
            self, repo_url: str, dest: Path, ref: str | None, *, defer_checkout: bool
    ) -> Repo:
        self._reset_dest(dest)
        try:
            # Defer checkout in sparse mode so cone patterns are set before the
            # working tree is written — avoids writing then pruning.
            return porcelain.clone(
                repo_url,
                target=str(dest),
                depth=1,
                branch=ref.encode() if ref else None,
                checkout=not defer_checkout,
            )
        except Exception as e:
            # `branch=` fails when ref is a raw sha (not an advertised ref).
            if ref:
                return self._clone_full(repo_url, dest, defer_checkout=defer_checkout)
            raise GitFetchError(f"failed to clone {repo_url}: {e}") from e

    def _clone_full(self, repo_url: str, dest: Path, *, defer_checkout: bool) -> Repo:
        """Full clone (no depth/branch) so an arbitrary sha is present."""
        self._reset_dest(dest)
        try:
            return porcelain.clone(
                repo_url, target=str(dest), checkout=not defer_checkout
            )
        except Exception as e:
            raise GitFetchError(f"failed to clone {repo_url}: {e}") from e

    # -- sparse checkout ---------------------------------------------------- #
    def _sparse_materialize(self, repo: Repo, subdir: str) -> None:
        """Cone-mode sparse checkout: only `subdir` lands in the working tree."""
        try:
            porcelain.cone_mode_init(repo)
            porcelain.cone_mode_set(repo, dirs=[subdir])
        except Exception as e:
            raise GitFetchError(f"failed sparse checkout of {subdir!r}: {e}") from e

    # -- ref resolution ----------------------------------------------------- #
    def _ensure_ref(self, repo: Repo, ref: str | None) -> None:
        """Guarantee HEAD is at `ref`, even when it was a raw sha."""
        if not ref:
            return
        if self._head_of(repo).startswith(ref):
            return
        try:
            porcelain.reset(repo, mode="hard", treeish=ref.encode())
        except Exception as e:
            raise GitFetchError(f"failed to checkout {ref!r}: {e}") from e

    # -- helpers ------------------------------------------------------------ #
    def _reset_dest(self, dest: Path) -> None:
        if dest.exists() and not self._keep_clone:
            shutil.rmtree(dest)

    @staticmethod
    def _head_of(repo: Repo) -> str:
        try:
            return repo.head().decode("ascii")
        except Exception:
            return ""

    @staticmethod
    def _assert_context_exists(context: Path, subdir: str | None) -> None:
        if not context.exists():
            hint = f" (subdir {subdir!r} not found in repo)" if subdir else ""
            raise GitFetchError(f"build context {context} does not exist{hint}")

    @staticmethod
    def _slug(repo_url: str) -> str:
        return repo_url.rstrip("/").split("/")[-1].removesuffix(".git")


class DulwichRefResolver(RemoteRefResolver):
    """Resolve a branch/tag to its commit sha via ls-remote (no clone)."""

    def resolve(self, repo_url: str, ref: str | None = None) -> str | None:
        try:
            refs = porcelain.ls_remote(repo_url)
        except Exception as e:
            raise GitFetchError(f"failed ls-remote {repo_url}: {e}") from e

        if ref is None:
            head = refs.get(b"HEAD")
            return head.decode("ascii") if head else None

        for key in (f"refs/heads/{ref}", f"refs/tags/{ref}", ref):
            val = refs.get(key.encode())
            if val:
                return val.decode("ascii")
        return None
