from . import *
from ..pydantic.pydantic import file, directory
from qcp_global_utils.util.import_helper import val_call
import signal, os, time


@validate_call
def run_shell_command(
    cmd:str, 
    positional_args: list=[],
    keyword_args: dict={},
    stdout_file: str|None='shell_output.out' , stderr_file: str|None='shell_output.err', 
    display_command: bool=False,
    uncritical:bool=False, time_limit: float|None=None,
    monitor_resources: bool=False,
    resources_refresh: float=2,
    periodic_check: Callable|None=None,
    refresh: float=2,
) -> Dict[str,Any]:
    """
        time_limit: time in seconds after which to abort execution automatically (not implemented yer)
        extra_return: error_code and pid

        NOT for running in the background at the moment
    """
    def decorate_command(cmd, positional_args:list=[], keyword_args:dict={}):
        """ 
        append positional and keyword arguments to the command string
        if value of dictionary is true then just give the key without an argument
        """
        args_line=[]

        for arg in positional_args:
            args_line+=[ f"{arg}"]

        for k,v in keyword_args.items():
            if isinstance(v, bool):
                if v:
                    args_line+=[ f"--{k}"] 
            else:
                args_line+=[ f"--{k} {v}" ]
        
        cmd=cmd if len(args_line)==0 else cmd+' '+' '.join(args_line) 
        return cmd

    cmd=decorate_command(cmd, positional_args, keyword_args)
    
    # Escape parentheses if they are not already escaped
    def escape_parentheses(cmd_str):
        """
        Escape ( and ) characters in the command string if they are not already escaped
        """
        result = ""
        i = 0
        while i < len(cmd_str):
            char = cmd_str[i]
            if char in ['(', ')']:
                # Check if it's already escaped (preceded by \)
                if i > 0 and cmd_str[i-1] == '\\':
                    # Already escaped, keep as is
                    result += char
                else:
                    # Not escaped, add escape
                    result += '\\' + char
            else:
                result += char
            i += 1
        return result
    
    cmd = escape_parentheses(cmd)

    com=f"There are already redirections (\'>\') in your command, provide them with designated keywords.\nSupplied command string was: \'{cmd}\'"
    if not stdout_file is None or stderr_file is not None:
        assert not '>' in cmd, com


    process_std=False
    if stdout_file is not None:
        process_std=True
        cmd=cmd+f" 1> {stdout_file}"
    if stderr_file is not None:
        process_std=True
        cmd=cmd+f" 2> {stderr_file}"

    # I may run my main window within a tmux session (or zoomed in whatsoever)
    # The output display will depend on that and maybe even get truncated (python rich)
    # COLUMNS should fix that within bashb
    if process_std:
        cmd=f"stty cols 120; {cmd}"  # on zsh also export COLUMNS=120 would work
    
    @val_call
    def get_out(base_str:str, the_file:file) -> str:
        with open(the_file,'r') as rd:
            content=rd.read().rstrip('\n')
            if len(content)==0: content=[]
            else: content=content.split('\n')
        return ([] if len(base_str)==0 else [base_str]) +content

    # Execute
    if display_command:
        print(f"# WILL RUN:\n    {cmd}")

    # start in a new session so we can reliably signal the whole group
    p = sp.Popen(
        cmd,
        shell=True,
        executable="/bin/bash",
        stderr=sp.PIPE,
        stdout=sp.PIPE,
        start_new_session=True,  # replaces preexec_fn=os.setsid
    )
    from .monitor_ressources import BackgroundProcessMonitor
    if monitor_resources:
        monitor=BackgroundProcessMonitor(p, refresh=resources_refresh).start()
    print(f"Started process with PID {p.pid}")

    def _terminate_process_group(proc: sp.Popen, *, kill_after_sec: float = 2.0) -> None:
        """Terminate (then kill) the whole process group of proc."""
        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            return  # already gone

        # First try graceful termination
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            return

        # Give it a moment
        t0 = time.time()
        while time.time() - t0 < kill_after_sec:
            if proc.poll() is not None:
                return
            time.sleep(0.05)

        # Escalate
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            return

    try:
        per_check={}
        if periodic_check is not None:
            time.sleep(refresh) # wait a bit before the first check, otherwise it may be too early
            di={}
            current=0
            while p.poll() is None:
                the_time=time.time()
                if the_time - current > refresh:
                    try:
                        di=periodic_check(p, di)
                    except Exception as e:
                        print(f"Error occurred during periodic check: {e}")
                    current=the_time
                time.sleep(refresh/20)
            per_check[getattr(periodic_check, "__name__").split(".")[-1]] = di
        if time_limit is None:
            stdout, stderr = [x.decode("utf-8") for x in p.communicate()]
            if stdout_file is not None:
                try:
                    stdout=get_out(stdout, stdout_file)
                except Exception as ex:
                    raise Exception(f"Could not read the output file \'{stdout_file}\' ({os.getcwd()}). {stderr}.\n Command was: {cmd}\n Original error: {ex}") from ex
            if stderr_file is not None:
                try:
                    stderr=get_out(stderr, stderr_file)
                except Exception as ex:
                    raise Exception(f"Could not read the output file \'{stderr_file}\' ({os.getcwd()}). {stderr}.\n Command was: {cmd}\n Original error: {ex}") from ex
        else:
            raise Exception("Time limit not implemented yet")
    except KeyboardInterrupt:
        _terminate_process_group(p, kill_after_sec=2.0)
        stdout_b, stderr_b = p.communicate()
        print(
            f"Process group for PID {p.pid} was interrupted by user (command was: '{cmd}'): "
            f"stderr: {stderr_b.decode('utf-8', errors='replace')}"
        ) 
        raise KeyboardInterrupt(f"Subprocess was running, and was terminated by user. Command was: '{cmd}'") from None
        
    if p.returncode!=0:
        message=f"Process {p.pid} failed with code {p.returncode} (command was: \'{cmd}\')"
        if not uncritical:
            raise Exception(message)
        else:
            print(message)

    if monitor_resources:
        try:
            monitor.stop()
            resources=monitor.stats()
        except Exception as e:
            print(f"Error occurred while stopping monitor: {e}")
            resources=None
    else:
        resources=None


    # Process the return

    return dict(
            stdout=stdout,
            stderr=stderr,
            pid=p.pid,
            returncode=p.returncode,
            resources=resources,
            **per_check,
    )
