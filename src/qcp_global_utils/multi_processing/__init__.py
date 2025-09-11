#from .. import *
from pydantic import BaseModel, validate_call, Field
val_cal=validate_call(config=dict(arbitrary_types_allowed=True))
from typing import Callable, List, Tuple, Union
import multiprocessing as mp