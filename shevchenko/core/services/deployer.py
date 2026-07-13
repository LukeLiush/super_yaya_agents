# shevchenko/services/deployer.py
from datetime import datetime, timezone

from shevchenko.contracts.plugins import BackendPlugin
from shevchenko.contracts.shapes import JobSpec, Coordinates
from shevchenko.core.deployment import Deployment, DeploymentFailed
from shevchenko.core.repository.deployment import DeploymentRepository
from shevchenko.core.repository.job import JobRepository
from shevchenko.core.values import JobId, Actor, DeploymentId, DeploymentStatus
from shevchenko.core.job import Job
from shevchenko.registry.plugin_registry import PluginRegistry


class Deployer:
    def __init__(
            self,
            plugin_registry: PluginRegistry,
            jobs: JobRepository,
            deployments: DeploymentRepository,
    ) -> None:
        self._plugin_registry = plugin_registry
        self._jobs = jobs
        self._deployments = deployments

    def deploy(
            self,
            job_id: JobId,
            technology: str,
            actor: Actor,
    ) -> Deployment:
        # 1. Load the registered job (the catalog entry).
        job: Job = self._jobs.get(job_id)

        # 2. Resolve the backend plugin by technology string.
        #    Deployer knows nothing about which backend this is.
        plugin: BackendPlugin = self._plugin_registry.get(technology)

        # 3. Build the agnostic spec to hand across the boundary.
        job_spec: JobSpec = JobSpec(
            id=job.id.value,
            version=job.version,
            io=job.io,
            container_artifact=job.artifact.to_container_artifact_contract(),
        )

        # 4. Delegate the actual placement to the plugin.
        #    The plugin does all the Prefect/Airflow/Inngest-specific work
        #    and returns opaque Coordinates.
        try:
            coordinates: Coordinates = plugin.deploy(job_spec)
        except Exception as e:
            raise DeploymentFailed(technology, job_id) from e

        # 5. Produce the core Deployment record — storing coordinates verbatim.
        deployment = Deployment(
            id=DeploymentId.create(),
            job_id=job.id,
            coordinates=coordinates,  # opaque, from plugin
            artifact=job.artifact,
            deployed_structure_hash=job.structure_hash,  # drift baseline
            status=DeploymentStatus.DEPLOYED,
            deployed_by=actor,
            deployed_at=datetime.now(timezone.utc),
        )

        # 6. Persist and return.
        self._deployments.save(deployment)
        return deployment
