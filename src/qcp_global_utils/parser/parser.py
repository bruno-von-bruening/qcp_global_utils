from qcp_global_utils.util.import_helper import * 

def check_is_controller(the_type):
    is_controller=False
    # For other controller class make recursive exmple
    import types
    if type(the_type)==types.UnionType:
        examples= [ x for x in the_type.__args__ if issubclass(x,controller_model) ]
        if len(examples)>1: raise Exception()
        if len(examples)>0:
            the_type=examples[0]
            is_controller=True
    elif issubclass(the_type, controller_model):
        is_controller=True
    return is_controller, the_type

class controller_model(BaseModel):
    class Config:
        arbitrary_types_allowed=True
        extra='forbid'
    __example_values__={}
    __default_values__={}

    def read_input_file(self, input):
        assert os.path.isfile(input), f"Not a file {input}"
        implemented_formats=['.yaml','.json']
        the_extension=[ x.strip('.') for x in implemented_formats if input.lower().endswith(x)]
        if len(the_extension)<1: f"Could not understand extension. Formats implemented: {implemented_formats}"
        assert len(the_extension)==1
        the_extension=the_extension[0]

        if the_extension=='yaml':
            with open(input, 'r') as rd:
                content=yaml.safe_load(rd)
        elif the_extension=='json':
            with open(input, 'r') as rd:
                content=json.load(rd)
        else: raise Exception(f"Unkown extension {the_extension}")
        return content
    
    def process_input(self, *args,**kwargs):
        """Input may by a positional argument or in kwargs
        I need to call this function in the inherited class itself
        """

        input=None
        # Check positionals
        if len(args)==1:
            input=args[0]
        elif len(args)>1: raise Exception(f"Expect maximum one positional argument")

        # Check keywords
        input_key='input'
        if input_key in kwargs.keys():
            assert input is None
            input=kwargs[input_key]
            del kwargs[input_key]
        
        if input is None:
            pass
        elif isinstance(input, str):
            content=self.read_input_file(input)
            
            assert isinstance(content, dict)

            for k,v in content.items():
                assert k not in kwargs.keys(), f"Double definition of key {k} (from file {input})"
            kwargs.update(content)

        else:
            raise Exception(f'Unexpected argument for \'{input_key}\': {input}, {type(input)}')
        args=[]
        return args, kwargs
    def __init__(self, *args,**kwargs):
        args,kwargs=self.process_input(*args,**kwargs)
        super().__init__(**kwargs)
    #@classmethod
    #def example(cls) -> dict:
    #    """ Provides an example of this class. This function was conceived to print out example file that the user can then manipulate. """
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
    def __init__(self, *args,**kwargs):
        input_key='input'
        if input_key in kwargs.keys():
            input=kwargs[input_key]
            del kwargs[input_key]
            if input is None:
                pass
            elif isinstance(input, str):
                assert os.path.isfile(input), f"Not a file {input}"
                implemented_formats=['.yaml','.json']
                the_extension=[ x.strip('.') for x in implemented_formats if input.lower().endswith(x)]
                if len(the_extension)<1: f"Could not understand extension. Formats implemented: {implemented_formats}"
                assert len(the_extension)==1
                the_extension=the_extension[0]

                if the_extension=='yaml':
                    with open(input, 'r') as rd:
                        content=yaml.safe_load(rd)
                elif the_extension=='json':
                    with open(input, 'r') as rd:
                        content=json.load(rd)
                else: raise Exception(f"Unkown extension {the_extension}")
                
                assert isinstance(content, dict)

                for k,v in content.items():
                    assert k not in kwargs.keys(), f"Double definition of key {k} (from file {input})"
                kwargs.update(content)

            else:
                raise Exception(f'Unexpected argument for \'{input_key}\': {input}, {type(input)}')
        super().__init__(**kwargs)
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
            the_type=value.annotation
            is_required=value.is_required()

            is_controller, the_type=check_is_controller(the_type)


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
                    # Deep copy is necessary to avoid yaml references.
                    example=the_type.example()
                elif not is_required:
                    example =value.default
                else:
                    example = f"<required argument of type {str(the_type)}>"
            
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
    def default_kwargs(cls) ->dict:

        base_kwargs=cls.example()
        defaults=cls.__default_values__

        for key, value in cls.__fields__.items():
            the_type=value.annotation
            is_required=value.is_required()

            is_controller, the_type=check_is_controller(the_type)

            if not is_controller:
                if key in defaults:
                    base_kwargs.update({key:defaults[key]})
            else:
                base_kwargs.update({key:the_type.default_kwargs()})
                
        return base_kwargs
    @classmethod
    def default(cls):
        kwargs=cls.default_kwargs()
        try:
            return cls(**kwargs)
        except Exception as ex: raise Exception()


    @classmethod
    def write_example(cls, output_file: str| None =None) -> file:
        content=cls.example()
        if output_file is None:
            output_file=cls.__name__+'_example.yaml'
        with open(output_file, 'w') as wr:
            yaml.safe_dump(content, wr)
        return output_file
    def write(self,output_file: str| None =None) -> file:
        content=self.model_dump()
        if output_file is None:
            output_file=type(self).__name__+'_example.yaml'
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