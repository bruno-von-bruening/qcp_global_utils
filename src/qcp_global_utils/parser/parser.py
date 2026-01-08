from . import *
import copy

from typing import Annotated, Literal, Tuple
from  pydantic import AfterValidator

from qcp_global_utils.environment.environment_variables import get_environment_var
import logging
logger = logging.getLogger(__name__)
# from .parser_helper import check_is_controller


def make_placeholder(v:str):
    return f"<{v}>"
def is_placeholder(v:str):
    if v.startswith('<') and v.endswith('>'):
        return True
    return False

def is_no_placeholder(v:str):
    if is_placeholder(v):
        raise ValueError(f"Value is a dummy placeholder: {v}")
    return v
my_str = Annotated[str, AfterValidator(is_no_placeholder)]

def handle_environment_var(string:str, expected_type:Literal['file']|None=None):
    the_return=get_environment_var(string)

    if expected_type is None: pass 
    elif expected_type=='file':
        assert os.path.isfile(the_return), f"Could process string '${string}' as enviroment variable, but value is not a file: {the_return}"
    else: raise Exception

    return the_return 

import types

def get_controller_types(the_type):
    if type(the_type)!= types.UnionType:
        return [the_type]
    return [ x for x in the_type.__args__ if issubclass(x,controller_model) ]


def convert_type(tp):
    """Return list of types or None from a Union (PEP 604 or typing.Union)."""
    # Case 1: plain type (not a union)
    if tp is None:
        return [tp]
    # Case 2: new-style union (PEP 604: X | Y)
    elif isinstance(tp, type):
        if isinstance(tp, (types.UnionType, Annotated)):
            return [t if t is not type(None) else None for t in get_args(tp)]
        else:
            return [tp]
    # Case 3: old-style typing.Union[X, Y]
    else:
        origin = getattr(tp, "__origin__", None)
        if isinstance(origin, type):
            return [origin]
        elif origin is types.UnionType or origin is Union or origin is Annotated or origin is None:
            return [t if t is not type(None) else None for t in get_args(tp)]
        else:
            raise Exception(tp)

def is_controller_type(the_type):
    if the_type is None:
        return False
    else:
        if isinstance(the_type, type):
            return issubclass(the_type, controller_model)
        else:
            types=convert_type(the_type)
            return any( is_controller_type(x) for x in  types)

def check_is_controller(the_type):
    is_controller=False
    # For other controller class make recursive exmple
    the_types=convert_type(the_type)

    # for x in the_types:
    #     print(x, type(x), x is  None)
    #     issubclass(x, controller_model)


    return any( is_controller_type(x) for x in the_types )

def process_input(*args,**kwargs):
    """Input may by a positional argument or in kwargs
    I need to call this function in the inherited class itself
    """
    @val_call
    def get_input(args:list, kwargs:dict) -> Tuple[str|None,dict]:
        input=None
        # Check positionals
        if len(args)==1:
            input=args[0]
        elif len(args)>1: raise Exception(f"Expect maximum one positional argument")

        # Check keywords 
        # -> confirm no double positional and keyword definition
        input_key='input'
        if input_key in kwargs.keys():
            assert input is None
            input=kwargs[input_key]
            del kwargs[input_key]
        return input, kwargs
    @val_call
    def process_input_inner(input:pdtc_file|str|None, kwargs:dict):
        """ 
        If input is None: do nothing, f"<{value}>"
        if string with dollarsign:  then check for file under environment variable, 
        if file: read the file
        """
        if input is None:
            pass
        elif isinstance(input, str):
            # Should be either environment variable that points to file or 
            if input.startswith('$'):
                input=handle_environment_var(input, expected_type='file')
            else:
                assert os.path.isfile(input), f"Input is not a file: {input}"
            
            # Read the file
            content=load_json_or_yaml(input)
            assert isinstance(content, dict), f"Expected to get find a dictionary but got {type(input)} from file: {input}"

            # Assert that loaded content does not overlap with already provided kwargs!
            # I guess we could also be lenient and allow kwargs to overwrite file
            for k,v in content.items():
                assert k not in kwargs.keys(), f"Double definition of key {k} (from file {input})"
            kwargs.update(content)
        else: raise Exception(f'Unexpected argument for \'{input_key}\': {input}, {type(input)}')

        return kwargs

    input,kwargs=get_input(args, kwargs)
    args=[]
    kwargs=process_input_inner(input, kwargs)

    return args, kwargs

class controller_model(BaseModel):
    class Config:
        arbitrary_types_allowed=True
        use_enum_values=True
        extra='forbid'
    directory: str|None =Field(default=None, exclude=True)
    filename: str|None =Field(default=None, exclude=True)# To remember file location to make relative paths work correctly
    __example_values__={}
    __default_values__={}

    #def read_input_file(self, input:pdtc_dump_file):
    #    content=load_json_or_yaml(input)
    #    return content

    @property
    def file_path(self):
        default_name=type(self).__name__+'.yaml'
        filename=self.filename if self.filename is not None else default_name
        return os.path.join(self.directory, filename )
    @staticmethod
    @val_call
    def make_placeholder(value:str):
        return make_placeholder(value)
    @staticmethod
    @val_call
    def is_placeholder(value:str):
        if len(value)>1:
            if value.startswith('<'):
                return True
            else: return False
        else:
            return False
    
    def __init__(self, *args,**kwargs):
        
        # Save location of file
        filename, directory=None,None
        if 'input' in kwargs.keys(): 
            filename=os.path.basename(kwargs['input'])
            directory=os.path.dirname(os.path.realpath(kwargs['input']))
        else: 
            # Could be inherited from upper class (if read as file)
            dir_hid='directory'; fi_hid='filename'
            if dir_hid in kwargs.keys():
                directory=kwargs[dir_hid]; del kwargs[dir_hid]
            else:
                directory=os.getcwd()
            if fi_hid in kwargs.keys():
                filename=kwargs[fi_hid]; del kwargs[fi_hid]

        # Args are made to kwargs (assuming that only on args exist and its the input)
        args,kwargs=process_input(*args,**kwargs)
        save_kwargs=copy.deepcopy(kwargs)


        for key, value in self.__fields__.items():
            the_type=value.annotation
            is_controler = check_is_controller(the_type)

            if key in kwargs.keys():
                if is_controler:
                    val=kwargs[key]
                    if isinstance(val, str):
                        # If relative path define to current file
                        kwargs.update({key: copy.deepcopy(the_type(self.get_file_path(val, directory=directory)).model_dump())})
                    elif not val is None:
                        kwargs[key].update({'filename':filename, 'directory':directory})
                else:
                    pass

        super().__init__(**kwargs)
        self.filename=filename
        self.directory=directory
    
    @staticmethod
    def decode_relative_path(fi:str, directory:pdtc_directory|None=None) -> pdtc_file:
        if fi.startswith('/'):
            return fi
        elif fi.startswith("$"):
            assert len(fi)>1, f"Provided only $: syntax error"
            key=fi[1:]
            if not key in os.environ.keys(): raise Exception(f"Could not find environment variable \'{fi}\'")
            else: return os.environ[key]
        else:
            if directory is None:
                raise Exception()
            else:
                realpath=os.path.realpath( os.path.join(directory, fi) )
                assert os.path.isfile(realpath)
                return realpath

    def get_file_path(self, fi, directory=None):
        if directory is None: directory=self.directory
        return self.decode_relative_path(fi, directory)

    def write(self, output_file: str| None =None) -> file:
        content=self.model_dump()
        if output_file is None:
            output_file=type(self).__name__+'_example.yaml'
        with open(output_file, 'w') as wr:
            yaml.safe_dump(content, wr, sort_keys=False)
        return output_file
    #    """ Provides an example of this class. This function was conceived to print out example file that the user can then manipulate. """
    #@classmethod
    #def example(cls) -> dict:
    #    # Could also just iterate over all method attributed and add a <fill-in> as value
    #    # -> elaborate on that later

    #    example_kwargs=cls.__example_values__


    #    # Make a dictionary of this class

    #    raise Exception()
    #    for key, value in cls.__fields__.items():
    #        if key in example_kwargs.keys():
    #            pass
    #        else:
    #            the_type=value.annotation
    #            is_required=value.is_required()
    #            
    #            # For other controller class make recursive exmple
    #            import types

    #            is_controller=False
    #            if type(the_type)==types.UnionType:
    #                examples= [ x for x in the_type.__args__ if issubclass(x,controller_model) ]
    #                if len(examples)>1: raise Exception()
    #                if len(examples)>0:
    #                    the_type=examples[0]
    #                    is_controller=True
    #            elif issubclass(the_type, controller_model):
    #                is_controller=True

    #            if is_controller:
    #                # Deep copy is necessary to avoid yaml references.
    #                example=the_type.example()
    #            elif not is_required:
    #                example =value.default
    #            else:
    #                example = f"<required argument of type {str(the_type)}>"
    #            example_kwargs.update( {key: example })
    #    # I could even return a class but then I would have to fill in required arguments with the right types
    #    #super().__init__(**cls._example_values)
    #    return example_kwargs 
    __example_values__={}
    @classmethod
    def example(cls, **kwargs) -> dict:
        """ Provides an example of this class. This function was conceived to print out example file that the user can then manipulate. """
        # Could also just iterate over all method attributed and add a <fill-in> as value
        # -> elaborate on that later

        import copy
        # Deecopy is essential, otherwise it overwrites example_values of other classes...
        example_kwargs=copy.deepcopy(cls.__example_values__)

        # Assert that example args are define fields
        defined_keys=list(cls.__fields__.keys())
        for k,v in example_kwargs.items():
            assert k in defined_keys, f"Example key {k} not in defined keys {defined_keys}"
        for k,v in kwargs.items():
            assert k in defined_keys, f"Provided key {k} not in defined keys {defined_keys}"


        # Make a dictionary of this class
        new_kwargs={}
        for key, value in cls.__fields__.items():
            if value.exclude:
                continue

            the_type=value.annotation
            is_required=value.is_required()

            is_controller = check_is_controller(the_type)


            if key in kwargs.keys():
                example=kwargs[key]
                if is_controller and isinstance(example,dict):
                    example=the_type.example(**example)
            elif key in example_kwargs.keys():
                example=example_kwargs[key]
                if is_controller and isinstance(example,dict):
                    example=the_type.example(**example)
            else:
                if is_controller:
                    the_types=get_controller_types(the_type)
                    if len(the_types)!=1:
                        raise Exception(f"Could not determine controller type for field {key} in class {cls.__name__}: {the_types}")
                    example=the_types[0].example()
                    # Deep copy is necessary to avoid yaml references.

                elif not is_required:
                    example =value.default
                else:
                    type_helper=the_type if not isinstance(the_type, EnumMeta) else f"str ({[ x.value for x in the_type]})"
                    example = f"<required argument of type {str(type_helper)}>"
            
            import copy
            if isinstance(example, BaseModel): 
                example=example.model_dump()
            if isinstance(example, (dict,list)):
                example=copy.deepcopy(example)
            new_kwargs.update( {key: example })
        example_kwargs.update(new_kwargs)
        # I could even return a class but then I would have to fill in required arguments with the right types
        #super().__init__(**cls._example_values)
        return example_kwargs 
    @classmethod
    def default_kwargs(cls, **kwargs) ->dict:

        base_kwargs=cls.example()
        defaults=cls.__default_values__

        fields=cls.__fields__

        # CHECK
        undefined=[ k for k in kwargs.keys() if k not in fields.keys() ]
        assert len(undefined)<1, f"Could not recognize keys {undefined}"

        # 
        for key, value in fields.items():

            # Some basic information
            the_type=value.annotation
            is_required=value.is_required()
            is_controller = check_is_controller(the_type)

            provided= (key in kwargs.keys())

            if is_controller:
                the_type=get_controller_types(the_type)
                if len(the_type)!=1:
                    raise Exception(f"Could not determine controller type for field {key} in class {cls.__name__}: {the_type}")
                the_type=the_type[0]
                value=the_type.default_kwargs()
                if provided: value.update(kwargs[key])
                base_kwargs.update({key:value})
            else:
                if not provided:
                    if key in defaults:
                        base_kwargs.update({key:defaults[key]})
                else:
                    base_kwargs.update({key:kwargs[key]})
        return base_kwargs
    @classmethod
    def default(cls, **kwargs):
        kwargs=cls.default_kwargs(**kwargs)
        try:
            return cls(**kwargs)
        except Exception as ex: raise Exception(f"Problem in initializing default of class {cls.__name__}: {ex}")


    @classmethod
    def write_example(cls, output_file: str| None =None) -> file:
        content=cls.example()
        if output_file is None:
            output_file=cls.__name__+'_example.yaml'
        with open(output_file, 'w') as wr:
            yaml.safe_dump(content, wr)
        return output_file

# https://stackoverflow.com/questions/67699451/make-every-field-as-optional-with-pydantic
# import pydantic
# from typing import Optional
# class AllOptional(pydantic.main.ModelMetaclass):
#     def __new__(self, name, bases, namespaces, **kwargs):
#         annotations = namespaces.get('__annotations__', {})
#         def recursion(item):
#             if issubclass(item, controller_model):
#                 return 
#             else:
#                 return item
# 
#         for base in bases:
#             annotations.update(base.__annotations__)
#         for field in annotations:
#             if not field.startswith('__'):
#                 annotations[field] = Optional[annotations[field]]
#         namespaces['__annotations__'] = annotations
#         return super().__new__(self, name, bases, namespaces, **kwargs)
# 
# class controller_model_example(controller_model, metaclass=AllOptional):
#     pass
