def _search_run_name() -> str:
    from prefect.runtime import task_run
    params = task_run.parameters
    sq = params["search_query"]
    q = sq.query if hasattr(sq, "query") else sq["query"]
    tr = sq.time_range if hasattr(sq, "time_range") else sq["time_range"]
    short_q = (q[:50] + "…") if len(q) > 50 else q        # bound the length
    return f"search [{tr}] {short_q}"