# e.g. sheva register  OR  the registration wizard backend
from pathlib import Path

from shevchenko.core.port.git import GitSource
from shevchenko.core.services.registration import RegistrationService
from shevchenko.core.values import Actor, JobManifest, Intent, IOContract, JobKey, Category, ParameterSet
from shevchenko.core.job import Job


def register_job(reg: RegistrationService, actor: Actor) -> Job:
    # Step 1 — point at the job source (or a prebuilt image)
    source = GitSource(
        repo_url="https://github.com/me/daily-stock",
        subdir=Path("finance_report/"),
    )

    # Step 2 — BUILD (or verify prebuilt) -> ContainerArtifact
    artifact = reg.build(source)

    # Step — DRAFT metadata (LLM proposes, provisional)
    job_manifest = JobManifest(
        intent=Intent(title="title1",
                      summary="summary",
                      description="description",
                      tags=[],
                      category=Category(value="finance"),
                      ))

    # Step 3 — CONFIRM (author edits the draft; here we just accept it)
    intent = job_manifest.intent  # in real UI: author reviews/overrides
    io = job_manifest.io

    # Step 4 — PUBLISH -> the Job catalog entry
    job = reg.register(
        job_key=JobKey(value="daily-stock-analysis"),
        job_intent=intent,
        io=io,
        artifact=artifact,
        kind="dag",
        actor=actor,
    )
    return job
    # ...later, entirely separately, the Deployer consumes this job.
