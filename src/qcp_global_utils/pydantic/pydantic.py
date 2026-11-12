from . import *
from pydantic import BeforeValidator, PlainSerializer
from typing import Annotated

import numpy as np

def check_ndarray(input):
    if isinstance(input, np.ndarray ):
        pass
    elif isinstance(input, (list,tuple) ):
        try:
            input=np.array(input)
        except Exception as ex:
            raise Exception(f"Could not convert to numpy array: {input}")
    return input

pdtc_ndarray=Annotated[ np.ndarray, BeforeValidator(check_ndarray) ]
    
# Pydantic classes for file and dictionary!
def check_dir(string):
    assert os.path.isdir(string),f"Not a valid directory: {string}"
    return string
def check_file(string):
    if isinstance(string, str):
        if  os.path.isfile(string):
            return string
        elif os.path.islink(string):
            return string
        else:
            raise ValueError(f"Not a valid file: {string}")
    else:
        raise ValueError(f"Not a string (so not even a file: {string}")
def check_dump_file(string):
    check_file(string)
    dump_extensions=['yaml','json']
    if not any([ string.lower().endswith('.'+x) for x in dump_extensions]):
        raise ValueError(f"Expected dump_file to end with one of  {dump_extensions}, got {string}")
    return string
directory=Annotated[str, BeforeValidator(check_dir)]
pdtc_file=Annotated[str, BeforeValidator(check_file)]
pdtc_dump_file=Annotated[str, BeforeValidator(check_dump_file)]
pdtc_directory=Annotated[str, BeforeValidator(check_dir)]

def list_to_string(the_list):
    return json.dumps(the_list)

my_list=Annotated[ List[int|float|str|pdtc_file], PlainSerializer(list_to_string) ]

from pydantic import ConfigDict
class myBaseModel(BaseModel):
    """ I do not like when extra keys are just ignored (usually they hide a mismatch in key string leading to erroneous read)
    arbitrary_types necessary for allowing non-standard types (like np.ndarray)
    """
    model_config=ConfigDict(
        arbitrary_types_allowed = True,
        extra = 'forbid'
    )

    if False: # old config Will be Deprecated and pushes warning 
        class Config:
            arbitrary_types_allowed = True
            extra = 'forbid'