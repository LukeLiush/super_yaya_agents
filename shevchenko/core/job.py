from datetime import datetime

from pydantic import BaseModel

from shevchenko.core.values import Intent, IOContract, JobId, ContainerArtifact, StructureHash, JobKey



class Job(BaseModel):
    key: JobKey
    version: int
    intent: Intent
    io: IOContract
    kind: str  # "dag" | "single_agent"  (display hint)
    structure_hash: StructureHash  # fingerprint of the registered spec
    created_by: str
    created_at: datetime
    artifact: ContainerArtifact  # the built+pushed image this job runs as

    def describe(self) -> str:  # convenience for UI/search
        return f"{self.intent.title}: {self.intent.summary}"
