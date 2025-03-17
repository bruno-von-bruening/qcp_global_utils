from . import *

from qc_global_utilities.shell_processes.execution import run_shell_command

@validate_call
def link_file(source:file, target:str|None=None, remove_old=True) -> file:
    if target is None:
        target='ln.'+os.path.basename(source)
    
    # If the link already exists, unlink it if remove_old is given
    if os.path.islink(target):
        if remove_old:
            print(f"Link {target} already existed, removing it")
            cmd='unlink {target}'
            run_shell_command(cmd)
        else:
            raise Exception(f"Link already exists and overwrite is not permitted")

    cmd=f"ln -s {source} {target}"
    run_shell_command(cmd)
    return target

# Temporary file
class choice(str, Enum):
    tmp = 'temporary'
    src = 'source'
class temporary_file_base(BaseModel):
    """ Source is the original file, tmp is a copy of it and which specifies which file to use
    """
    source: file
    tmp_file: file | None
    which:  choice = choice.tmp
    @property
    def file(self):
        if self.which==choice.tmp:
            assert self.tmp_file is not None, f"Excepected to use temporary file but none has been define"
            return self.tmp_file
        elif self.which==choice.src:
            return self.source
    def check(self):
        if self.tmp_file is not None:
            assert os.path.isfile(self.source), f"Source file corrupted ({self.source} is not a file): quiting for safety"
            assert os.path.realpath(self.source)!=os.path.realpath(self.tmp_file), f"error in this class tmp_file is source file, dangerous since source could be destroyed"
        return True

class temporary_file(temporary_file_base):
    """
    Recognizes if file is linked or compressed file. 
    If not:
        works with original file
    Else:
        works with uncomprsessed copy of the file
    """
    def __init__(self, fi, copy=False):
        # In case its a symlink copy to local dir
        source=fi
        info=self.handle_source(source,copy)
        super().__init__(**info)

    def handle_source(self,source, copy):
        # If its a link unlink first
        tmp_file=source

        # Copy file?
        is_link=os.path.islink(tmp_file)
        is_compressed=any([ tmp_file.upper().endswith(ext.upper()) for ext in ['.gz','.xz']])
        if any([is_link, is_compressed, copy]):
            old_file=tmp_file
            tmp_file='tmp.'+os.path.basename(tmp_file)
            run_shell_command(f"cp {os.path.realpath(old_file)} {tmp_file}")
            assert os.path.isfile(tmp_file), f"Expected but does not exist: {tmp_file} (pwd: {os.getcwd()})"
            which=choice.tmp            

        ## Unpack 
        def decompress(tmp_file):
            extensions=['gz','xz']
            scripts={ #executbale for the given extension
                'gz':'gzip',
                'xz':'xz',
            }
            def get_ext(tmp_file):
                found=[ x for x in extensions if tmp_file.endswith('.'+x)]
                assert len(found)==1, f"Cannot find extension (options={extensions}) for file: {tmp_file}"
                return found[0]
            ext=get_ext(tmp_file)

            uncomp_file=tmp_file.replace(f".{ext}",'')
            exec=scripts[ext]
            cmd=f"{exec} -d {tmp_file}"
            run_shell_command(cmd)
            assert os.path.isfile(uncomp_file), f"Cannot find the file that should result from the \'{ext}\'-decompression ({cmd}): {uncomp_file}"
            return uncomp_file
        if is_compressed:
            tmp_file=decompress(tmp_file)
            

        # If the tmp file is the same as source, then there is no tmp_file
        if os.path.realpath(tmp_file)==os.path.realpath(source):
            if copy:
                tmp_file='tmp.'+os.path.basename(source)
                run_shell_command(f"cp {source} {tmp_file}")
                assert os.path.isfile(tmp_file)
                which=choice.tmp
            else:
                tmp_file=None
                which=choice.src
        else:
            which=choice.tmp
        # Assert the file lies in this directory and it exists
        def check_same_dir(tmp_file):
            return os.path.relpath(os.path.dirname(os.path.realpath(tmp_file)),os.getcwd())=='.'
        if tmp_file is not None:
            if not check_same_dir(tmp_file): raise Exception(f"Tmp file should be in present working directory ({os.getcwd()})\n{tmp_file}")

        return dict(
            source=source,
            tmp_file=tmp_file,
            which=which
        )

    def remove_tmp(self, verbose=True):
        self.check()
        if self.tmp_file is not None:
            cmd=f"rm {self.tmp_file}"
            run_shell_command(cmd)
            if verbose: print(f"Deleted temporary file {self.tmp_file}")
