from . import *
import multiprocessing as mp


class job(BaseModel):
    function: Callable
    args: List = []
    kwargs: dict ={}
class job(job):
    def run(self):
        return self.function( *self.args, **self.kwargs)

@val_cal
def spawn_workers(jobs:List[job], num_processes:int):
    """ Provide the job_list and this will be run in parallel """

    pool=mp.Pool(processes=num_processes)

    assert len(jobs)<=num_processes, f"More jobs than processes, batching system not implemented yet (think also about using queueing system)"
    Runs=[]
    for job in jobs:
        run=pool.apply_async(job.function, [job.args, *job.kwargs ])
        Runs.append(run)
                
    finished_jobs=[]
    for run in Runs:
        out=run.get()
        finished_jobs+=[out]
    return finished_jobs


from . import *




@val_cal
def make_queue(jobs:List[job], number_of_workers:int=Field(default=1, ge=1)) -> List:
    def job_wrapper(queue_todo,queue_done):
        """ As long as there are items in the queue continue processing the next item"""
        while not queue_todo.empty():
            instruction=queue_todo.get()
            id=instruction['id']
            j=job(**instruction['job'])
            
            the_return = j.run()

            queue_done.put({'id':id,'job':j.model_dump(), 'return':the_return})

    import os
    max_processes=os.cpu_count()
    buffer=4
    assert max_processes>buffer
    if number_of_workers>max_processes-buffer:
        print(f"WARNING: Requested of number of workers ({number_of_workers}) is larger than number of available cores {max_processes} minus buffer={buffer}. Setting number of workers to {max_processes-buffer}")
        number_of_workers=max_processes-buffer
    print(f"Got {len(jobs)} jobs.")
    # Get an id for every job
    jobs_with_id=[]
    for id,j in enumerate(jobs):
        jobs_with_id.append( {'id':id,'job':j.model_dump()})
    
    # Prepare the queue
    q=mp.Queue()
    q_done=mp.Queue()
    [ q.put(x) for x in jobs_with_id ]

    # Start the runs
    processes=[ mp.Process(target=job_wrapper, args=(q,q_done)) for i in range(number_of_workers) ]
    for p in processes:
        p.start()

    # wait for the runs
    import tqdm
    import time
    len_queue=len(jobs)
    old_qsize=0
    with tqdm.tqdm(total=len_queue, initial=old_qsize, dynamic_ncols=True) as pbar:
        while True:
            qsize=q_done.qsize()
            pbar.total = len_queue
            if qsize!=old_qsize:
                pbar.update(qsize-old_qsize)
                    # pbar.set_postfix(
                    #     {
                    #         "r,f,w": (pending,failed,recent_worker),
                    #     }
                    # )
            old_qsize=qsize
            if qsize>=len_queue:
                break
            time.sleep(.2)
    for p in processes:
        p.join()

    # Return the results (in the order of jobs received)
    assert q_done.qsize()==len(jobs)
    results=[ q_done.get() for i in range(q_done.qsize())]
    results_sort=sorted(results, key=lambda x:x['id'])
    return [ r['return'] for r in results_sort ]






