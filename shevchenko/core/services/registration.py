# shevchenko/services/registration.py
import hashlib
import json
from datetime import datetime, timezone

from shevchenko.core.port.git import ImageBuilder, JobSource
from shevchenko.core.repository.job import JobRepository
from shevchenko.core.values import Actor
from shevchenko.core.values import ContainerArtifact, StructureHash, JobKey
from shevchenko.core.values import IOContract
from shevchenko.core.values import Intent
from shevchenko.core.job import Job
from shevchenko.core.values import JobManifest


class RegistrationService:
    def __init__(
            self,
            jobs: JobRepository,
            image_builder: ImageBuilder,
    ) -> None:
        self._jobs = jobs
        self._image_builder = image_builder

    # ── Stage 2: BUILD — turn source into a runnable artifact ──────────
    def build(self, job_source: JobSource, ) -> ContainerArtifact:
        """Build+push (or verify a prebuilt image) and return the artifact
           with its immutable digest."""
        artifact = self._image_builder.resolve(job_source)
        return artifact

    # ── Stage 3: REGISTER — create the Job catalog entry ──────────
    def register(
            self,
            job_key: JobKey,
            job_intent: Intent,
            io: IOContract,
            artifact: ContainerArtifact,
            kind: str, # TODO enum?
            actor: Actor,
    ) -> Job:
        """Confirmed metadata + built artifact -> a published Job.
           This produces the object the Deployer later consumes."""

        # Assign the next version for this key (immutable versioning).
        job_version: int = self._next_version(job_key)

        # Compute the structure fingerprint — INCLUDING the image digest,
        # so a rebuilt image counts as a change (drift baseline correctness).
        structure_hash: StructureHash = self._compute_structure_hash(io, artifact, kind)

        job = Job(
            key=job_key,
            version=job_version,
            intent=job_intent,
            io=io,
            kind=kind,
            artifact=artifact,
            structure_hash=structure_hash,
            created_by=actor.id,
            created_at=datetime.now(timezone.utc),
        )

        self._jobs.save(job)  # commit the catalog entry
        return job

    # ── helpers ────────────────────────────────────────────────────────
    def _next_version(self, job_key: JobKey) -> int:
        existing: list[int] = self._jobs.list_versions(job_key)
        return (max(existing) + 1) if existing else 1

    @staticmethod
    def _compute_structure_hash(
            io: IOContract, artifact: ContainerArtifact, kind: str
    ) -> StructureHash:
        material = {
            "io": io.model_dump(),
            "digest": artifact.image.digest,  # rebuild -> new hash -> drift
            "kind": kind,
        }
        blob = json.dumps(material, sort_keys=True)
        return StructureHash(value=hashlib.sha256(blob.encode()).hexdigest())
