from . import *

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
    if  os.path.isfile(string):
        return string
    elif os.path.islink(string):
        return string
    else:
        raise ValueError(f"Not a valid file: {string}")
directory=Annotated[str, BeforeValidator(check_dir)]
file=Annotated[str, BeforeValidator(check_file)]

def list_to_string(the_list):
    return json.dumps(the_list)

my_list=Annotated[ List[int|float|str|file], PlainSerializer(list_to_string) ]