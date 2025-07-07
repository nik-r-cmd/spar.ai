import asyncio
from typing import Callable, Awaitable, Optional
from .input_handler import SubtaskDAG, Subtask

async def orchestrate_dag(
    dag: SubtaskDAG,
    subtask_executor: Callable[[Subtask], Awaitable],
    update_callback: Optional[Callable[[SubtaskDAG], None]] = None,
    max_retries: int = 1
) -> SubtaskDAG:
    """
    Orchestrate execution of a SubtaskDAG in parallel where possible.
    subtask_executor: async function to run a subtask (should set subtask.result/status).
    update_callback: called after each subtask finishes (for UI updates).
    max_retries: number of retries for failed subtasks.
    Returns the final SubtaskDAG with updated statuses/results.
    """
    pending = set(dag.subtasks.keys())
    running = set()
    completed = set()
    failed = set()
    retries = {name: 0 for name in dag.subtasks}

    async def run_subtask(subtask: Subtask):
        subtask.status = 'running'
        try:
            await subtask_executor(subtask)
            subtask.status = 'done'
        except Exception as e:
            subtask.error = str(e)  # type: ignore
            retries[subtask.name] += 1
            if retries[subtask.name] <= max_retries:
                subtask.status = 'pending'  # retry
            else:
                subtask.status = 'failed'
        if update_callback:
            update_callback(dag)

    while pending:
        # Find all ready subtasks
        ready = [s for s in dag.get_ready_subtasks() if s.name in pending and s.status == 'pending']
        if not ready:
            # Deadlock or all running/failed
            break
        tasks = [asyncio.create_task(run_subtask(subtask)) for subtask in ready]
        for subtask in ready:
            running.add(subtask.name)
            pending.remove(subtask.name)
        await asyncio.gather(*tasks)
        # Update completed/failed
        for name, subtask in dag.subtasks.items():
            if subtask.status == 'done':
                completed.add(name)
            elif subtask.status == 'failed':
                failed.add(name)
        # Re-add failed subtasks for retry if allowed
        for name in dag.subtasks:
            if dag.subtasks[name].status == 'pending' and name not in pending:
                pending.add(name)
    return dag 