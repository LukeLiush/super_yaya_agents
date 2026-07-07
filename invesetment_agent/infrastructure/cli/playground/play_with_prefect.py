import random
import time
from typing import ClassVar, Literal

from prefect import flow, pause_flow_run, task
from prefect.input import RunInput
from prefect.runtime import deployment, flow_run


class AdditionalItems(RunInput):
    # the human fills this in via the UI form
    extra_items: str = ""  # comma-separated items to add, e.g. "refunds, invoices"


class ItemSelection(RunInput):
    # rendered as a selection in the UI because the type is a constrained Literal
    selected_items: ClassVar[list[Literal["refunds", "invoices", "shipments"]]] = []


@task
def discover_items() -> list[str]:
    items: list[str] = ["users", "orders", "payments"]
    return items


@task(log_prints=True)
def process(table: str):
    print(f"Processing {table}")
    # Generate a random sleep duration between 3 and 10 seconds
    sleep_time = random.uniform(3, 10)
    print(f"Sleeping for {sleep_time:.2f} seconds...")
    time.sleep(sleep_time)
    return f"{table}_done"


@flow(log_prints=True, name="Fanout Flow")
async def fanout_flow():
    print(deployment.version)  # the deployment's version string
    print(deployment.id)  # deployment ID
    print(deployment.name)  # deployment name
    print(flow_run.id)  # current flow run ID
    tables = discover_items()

    # --- Human in the loop: let a user add more items before fan-out ---
    user_input = await pause_flow_run(
        # wait_for_input=AdditionalItems,
        wait_for_input=ItemSelection,
        timeout=600,  # wait up to 10 min, then fail rather than hang forever
    )
    if user_input.selected_items:
        print(f"User selected: {user_input.selected_items}")
        # dedupe in case a user picks something already discovered
        tables = tables + [i for i in user_input.selected_items if i not in tables]

    # print(f"Final item list: {tables}")
    # extra = [s.strip() for s in user_input.extra_items.split(",") if s.strip()]
    # if extra:
    #     print(f"User added: {extra}")
    #     tables = tables + extra

    print(f"Final item list: {tables}")

    # one concurrent task per discovered item — count not known in advance
    futures = [process.submit(table) for table in tables]
    results = [future.result() for future in futures]
    print(results)


if __name__ == "__main__":
    import asyncio
    from typing import Any, cast

    asyncio.run(cast(Any, fanout_flow)())
    # fanout_flow.serve()
    # fanout_flow.deploy(
    #     name="my_deploy_1",
    #     work_pool_name="docker_worker_pool1",
    #     image="etl-pipeline:latest",  # plain local name
    #     push=False,
    #     job_variables={"image_pull_policy": "IfNotPresent"}  # don't pull when running
    # )
