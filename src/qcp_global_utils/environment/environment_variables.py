from . import *

def get_environment_var(string:str):
    if string.startswith('$'):
        assert len(string)>0, f"string is only dollar sign: {string}"
        string=string[1:]
    else:
        assert len(string)>0, f"Provided empty string"

    assert string in os.environ.keys(), f"Provided environment variable {string} but cannot be found"
    the_return=os.environ[string]
    assert len(the_return)>1, f"Could process '${string}' as environment variable, but this variable is empty!"

    return the_return
