from qcp_global_utils.pydantic.pydantic import pdtc_file
import subprocess as sp, re
from .helper import VERSION_EXPECTED_FORM, VERSION_EXPECTED_FORM_READABLE

def get_foreign_version(python_executable: pdtc_file, module_name:str) -> str:
    """ Wanna get version of package in python executable of other python environment"""
    cmd=f"{python_executable} -c \"import {module_name}; print({module_name}.__version__)\""
    try:
        proc=sp.run(
            cmd,
            shell=True, executable='/bin/bash',
            stdout=sp.PIPE, stderr=sp.PIPE,
            check=False,
            text=True,
        )
        version = proc.stdout.strip()
        if proc.returncode != 0:
            raise Exception(f"Command '{cmd}' failed with error: {proc.stderr.strip()}")
        assert re.fullmatch(VERSION_EXPECTED_FORM, version), f"Cannot process version '{version}'. Expected format: {VERSION_EXPECTED_FORM_READABLE}"
    except Exception as ex:
        raise Exception(f"Could not get foreign version using command '{cmd}': {ex}")
    return version
    
