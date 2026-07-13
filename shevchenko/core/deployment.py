# shevchenko/core/deployment.py  — the record the deployer PRODUCES & persists
from datetime import datetime

from pydantic import BaseModel

from shevchenko.contracts.shapes import Coordinates
from shevchenko.core.values import DeploymentId, JobId, ContainerArtifact, StructureHash, DeploymentStatus, Actor


class DeploymentFailed(Exception):
    pass


class Deployment(BaseModel):
    id: DeploymentId
    job_id: JobId
    coordinates: Coordinates  # stored verbatim, from the plugin
    artifact: ContainerArtifact
    deployed_structure_hash: StructureHash
    status: DeploymentStatus
    deployed_by: Actor  # provenance
    deployed_at: datetime
