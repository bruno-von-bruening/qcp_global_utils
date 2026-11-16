from . import *
import time, re

from qcp_global_utils.pydantic.pydantic import myBaseModel

def now():
    return time.time()

class time_point(myBaseModel):
    """ Captures the timing of a single event (between two different markers)"""
    key:        str
    time:       float
    @validate_call
    def __init__(self, key:str, time: float|None=None):
        if time is None:
            time=now()
        super().__init__(key=key, time=time)
class period(myBaseModel):
    start_key: str
    end_key: str
    time_start: float
    time_end: float
    def print(self):
        print(f"TIMING: {self.time_end-self.time_start:.4f} [s] for completion of \'{self.end_key}\'")
    def info(self):
        return {
            'start_key':self.start_key,
            'end_key':self.end_key,
            'duration':self.time_end-self.time_start
        }

class Tracker_data(myBaseModel):
    messages    : my_list=[]
    warnings    : my_list=[]
    errors      : my_list=[]
    time_start  : float|None=None
    time_end    : float|None=None
    time_points: List[time_point]=[]
    periods:    List[period]=[]

class Tracker(Tracker_data):
    def __init__(self, *args, **kwargs):
        time_start=time.time()
        super().__init__(*args, **kwargs, time_start=time_start)
        self.add_time_point('start', time=self.time_start)
    @validate_call
    def model_dump(self, content:str|None=None):
        self.stop()
        return super().model_dump()
    def info_dic(self, keys=['messages','warnings','errors'] ):
        self.stop()
        base_dic=super().model_dump(include=keys)
        base_dic.update({'elapsed_time':self.time_end-self.time_start})
        return base_dic
    def timings_dic(self):
        self.stop()
        timings=[ x.info() for x in self.periods ]
        time_points=super().model_dump(include=['time_points'])['time_points']
        return {'timings':timings, 'time_points':time_points}
    def stop(self):
        if self.time_end is None:
            self.time_end=time.time()
            self.add_time_point( 'end', time=self.time_end)
        
class Tracker(Tracker):
    def add_message(self, x):
        self.messages.append(x)
    def add_warning(self, x):
        self.warnings.append(x)
    def add_error(self, x):
        self.errors.append(str(x))
    @property
    def no_error(self):
        return len(self.errors)<1
    @property
    def no_warning(self):
        return len(self.warnings)<1
    @property
    def status(self):
        return self.process_status(self, code=False)
    @property
    def status_code(self):
        return self.process_status(self, code=True)
    ## Add intermediary stops
    @validate_call
    def add_time_point(self, key:str, time: float | None = None):
        self.time_points.append(time_point(key, time))
    @validate_call
    def add_period(self, start_key: str|None=None, end_key: str|None=None, print=False):

        def raise_error(message):
            print(f"Non critical error in requesting period: {message}")

        time_points=self.time_points

        # if not enough points are there then we cannot get a period (but dont crash the process)
        if len(time_points)<2:
            error_message="Requested print but less than two time points have been recorded."
            return raise_error(error_message)
        
        @validate_call 
        def search_time(time_points: List[time_point], key:str):
            found=[ (i,x.key) for i,x in enumerate(time_points) if re.fullmatch(key,x.key, re.IGNORECASE) ]
            if len(found)!=1:
                return raise_error(error_message)
            else:
                return found[0][0]

        if start_key is None:
            start=-2
        else:
            start=search_time(self.time_points, start_key)
        if end_key is None:
            end=-1
        else:
            end=search_time(self.time_points, end_key)

        if not start<end:
            error_message=f"Error in assigning numbers, end is not behind start: (start_index={start}, end_index={end})"
            return raise_error(error_message)

        kwargs=dict( 
            start_key=time_points[start].key, end_key=time_points[end].key,
            time_start=time_points[start].time, time_end=time_points[end].time,
        )
        per=period(**kwargs)
        self.periods.append( per )
        if print:
            per.print()

        
        



            

    
    def get_status(self):
        dic=self.model_dump()
        dic.update({'status':self.status, 'status_code':self.status_code})
        return dic
    def process_status(self, code=False):
        if self.no_error and self.no_warning:
            ret=(f"Run finished normally",1)
        elif self.no_error and not self.no_warning:
            ret=(f"Run finished with warning(s)",2)
        elif not self.no_error:
            if self.no_warning:
                ret=(f"Run finished with error(s)",0)
            else:
                ret=(f"Run finished with error(s) and warning(s)",0)
        else:
            raise Exception(f"Forgot case")

        if code:
            return ret[1]
        else:
            return ret[0]