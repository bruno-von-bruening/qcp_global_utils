from . import *

from qcp_global_utils.shell_processes.execution import run_shell_command

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
        # Assert that source is not in pwd (also considers the file a link it pointing to [gets dereferenced with realpath])        
        #assert os.getcwd()!=os.path.dirname(os.path.realpath(source)), f"Source file is in current working directory: {os.path.realpath(source)}"


        # Make a copy of this file
        tmp_file='tmp.'+os.path.basename(source)
        run_shell_command(f"cp {os.path.realpath(source)} {tmp_file}")
        assert os.path.isfile(tmp_file), f"Expected but does not exist: {tmp_file} (pwd: {os.getcwd()})"

        ## Unpack 
        def decompress(tmp_file, delete_old=False):
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
            cmd=f"{exec} -d {'-k' if not delete_old else ''} {tmp_file}"
            run_shell_command(cmd)
            assert os.path.isfile(uncomp_file), f"Cannot find the file that should result from the \'{ext}\'-decompression ({cmd}): {uncomp_file}"
            return uncomp_file
        
        # In case this file is compressed, decompress it and delete the compressed file
        is_compressed=any([ tmp_file.upper().endswith(ext.upper()) for ext in ['.gz','.xz']])
        if is_compressed:
            tmp_file=decompress(tmp_file, delete_old=True)
            

        # Assert the file lies in this directory and it exists
        def check_same_dir(tmp_file):
            return os.path.relpath(os.path.dirname(os.path.realpath(tmp_file)),os.getcwd())=='.'
        #if tmp_file is not None:
        #    if not check_same_dir(tmp_file): raise Exception(f"Tmp file should be in present working directory ({os.getcwd()})\n{tmp_file}")

        assert check_same_dir(tmp_file), f"Expected temporary file to be in pwd: {os.getcwd()} {tmp_file}"

        the_which=choice.tmp
        return dict(
            source=source,
            tmp_file=tmp_file,
            which=the_which
        )

    def remove_tmp(self, verbose=True):
        self.check()
        if self.tmp_file is not None:
            cmd=f"rm {self.tmp_file}"
            run_shell_command(cmd)
            if verbose: print(f"Deleted temporary file {self.tmp_file}")
    def remove_src(self, verbose=True):
        self.check()
        cmd=f"rm {self.source}"
        run_shell_command(cmd)
        if verbose: print(f"Deleted source file {self.tmp_file}")
    @val_call
    def delete_all(self, tag=Literal['tmp','temporary','source','src','all'] , verbose=True):
        if tag in ['tmp','temporary']:
            self.remove_tmp(verbose=verbose)
        elif tag in ['src','source']:
            self.remove_src(verbose=verbose)
        elif tag in ['all']:
            self.remove_src(verbose=verbose)
            self.remove_tmp(verbose=verbose)

@val_call
def load_json_or_yaml(the_file:file) -> Tuple[dict, list]:
    """ """ 
    def read_the_file(the_file):
        # Read the file
        with open(the_file, 'r') as rd:
            content=rd.read()
        
        # Process the content to object
        if the_file.upper().endswith( '.JSON' ):
            content=json.loads(content)
        elif the_file.upper().endswith( '.YAML' ):
            content=yaml.save_load(content)
        else:
            raise Exception(f"Unkown ending of file (\'{the_file}\')")
        return content
    
    try:
        content=read_the_file(the_file)
    except Exception as ex:
        raise Exception(f"Could not process file (\'{the_file}\') as yaml or json file:\n error={ex}")

    return content

@validate_call
def compress_file(the_file:file, compression_type:str='xz', compression_level:int|None=None) -> file:
    """
    Compresses file with either xz or gz method
    Could also implement thread usage for xz if performance needs to be improved
    """

    known_compression=['xz','gz']
    assert compression_type in known_compression, f"Unkown compression type: \'{compression_type}\'"

    comp_level=f"-{compression_level}" if compression_level is not None else ''
    
    run_shell_command(
        ' '.join([compression_type, comp_level, the_file ]) 
    )
    compressed_file=f"{the_file}.xz"
    assert  os.path.isfile(compressed_file), compressed_file

    return compressed_file