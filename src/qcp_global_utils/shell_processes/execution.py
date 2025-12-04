from . import *
from ..pydantic.pydantic import file, directory

@validate_call
def run_shell_command(
    cmd:str, 
    positional_args: list=[],
    keyword_args: dict={},
    stdout_file: str|None='shell_output.out' , stderr_file: str|None='shell_output.err', 
    display_command: bool=False,
    uncritical:bool=False, time_limit: float|None=None
) -> Tuple[str, str]:
    """
        time_limit: time in seconds after which to abort execution automatically (not implemented yer)
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

    if stdout_file is not None:
        cmd=cmd+f" 1> {stdout_file}"
    if stderr_file is not None:
        cmd=cmd+f" 2> {stderr_file}"
    @validate_call
    def get_out(base_str:str, the_file:file) -> str:
        with open(the_file,'r') as rd:
            content=rd.read()
        content=' | '.join([base_str, content])
        return content
        
    # Execute
    if display_command:
        print(f"# WILL RUN:\n    {cmd}")
    p=sp.Popen(cmd, shell=True, stderr=sp.PIPE, stdout=sp.PIPE)
    if time_limit is None:
        stdout, stderr = [x.decode('utf-8') for x in p.communicate() ]
        if stdout_file is not None:
            try:
                stdout=get_out(stdout, stdout_file)
            except Exception as ex:
                raise Exception(f"Could not read the output file \'{stdout_file}\' ({os.getcwd()}). {stderr} Original error: {ex}") from ex
        if stderr_file is not None:
            try:
                stderr=get_out(stderr, stderr_file)
            except Exception as ex:
                raise Exception(f"Could not read the output file \'{stdout_file}\' ({os.getcwd()}) . Original error: {ex}") from ex
    else:
        raise Exception(f"Time limit not implemented yet")


    # Process the return
    if p.returncode!=0:
        message=f"The command \'{cmd}\' failed:\n{stderr}"
        if not uncritical:
            raise Exception(message)
        else:
            print(message)
    return stdout, stderr
