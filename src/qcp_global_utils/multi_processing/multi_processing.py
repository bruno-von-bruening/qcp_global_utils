from . import *
import multiprocessing as mp



@validate_call
def spawn_workers(jobs:List[dict], num_processes:int):
    """ Provide the job_list and this will be run in parallel """

    pool=mp.Pool(processes=num_processes)

    assert len(jobs)<=num_processes, f"More jobs than processes, batching system not implemented yet (think also about using queueing system)"
    Runs=[]
    for job in jobs:
        the_function=job['function']
        args=job['args']
        kwargs=job['kwargs']
        run=pool.apply_async(the_function , [ args, *kwargs] )
        Runs.append(run)
                
    finished_jobs=[]
    for run in Runs:
        out=run.get()
        finished_jobs+=[out]
    return finished_jobs
    

