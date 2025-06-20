from . import *

def get_conda_base() -> directory:
    """ Return base bath of conda setup (through conda executable)"""

    # Get the conda executable
    conda_exe_var='CONDA_EXE'
    if not conda_exe_var in os.environ.keys():
        raise Exception(f"NO environment variable \'{conda_exe_var}\'")
    conda_exe_path=os.environ[conda_exe_var]

    # Truncate the end to get base path
    assert conda_exe_path.endswith('bin/conda'), conda_exe_path
    conda_exe_path=conda_exe_path.replace('bin/conda','')

    assert os.path.isdir(conda_exe_path), f"Conda base environment assumed to be \'{conda_exe_path}\' but is not a directory!"
    return conda_exe_path


@validate_call
def get_python_from_conda_env(env_name: str, base:directory=None
    ) -> file:
    if isinstance(base, type(None)):
        base=get_conda_base()
    assert isinstance(base, str)
    assert isinstance(env_name, str)

    python=os.path.join(base, 'envs', env_name, 'bin','python')
    assert os.path.isfile(python), f"Cannot find python executable under {python}, does the environment {env_name} exist on this machine?"
    return python