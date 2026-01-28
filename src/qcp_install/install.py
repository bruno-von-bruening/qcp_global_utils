from qcp_global_utils.pydantic.pydantic import pdtc_file
from qcp_global_utils.environment.file_handling import load_json_or_yaml
from qcp_global_utils.environment.environment_variables import get_environment_var
from qcp_global_utils.shell_processes.execution import run_shell_command
from pydantic import validate_call; val_call=validate_call(config=dict(arbitrary_types_allowed=True))
import os

@val_call
def source_conda():
    conda_exe_var='CONDA_EXE'
    conda_exe=get_environment_var(conda_exe_var)
    assert os.path.isfile(conda_exe), f"Expected to find executable at {conda_exe} und ${conda_exe_var}, but not found."

    # get the conda source
    conda_exe_dir='bin/conda'
    assert conda_exe.endswith(conda_exe_dir)
    base=f"{conda_exe.replace(conda_exe_dir, '')}/etc/profile.d/conda.sh"
    assert os.path.isfile(base), "Expected file '${base}'"

    return base


@val_call
def conda_update_env(conda_file:pdtc_file ):
    conda_source=source_conda()

    content=load_json_or_yaml(conda_file)

    cmd=' && '.join([
        f"source {conda_source}",
        f"$CONDA_EXE init bash",
        f"conda activate base",
        f"conda env update -f \"{conda_file}\"  --prune",
        f"conda deactivate",
    ])
    print(f"Will update/install conda environment {content['name']} from file {conda_file}...")
    try:
        print(f"RUNNING: {cmd}")
        run_shell_command(cmd)
        print(f"Successfully updated conda environment {content['name']}.")
    except Exception as ex: 
        raise Exception(f"Could not update conda environment {content['name']}: {ex}")

