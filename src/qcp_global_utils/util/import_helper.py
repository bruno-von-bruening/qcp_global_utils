from pydantic import PrivateAttr,BaseModel, Field, validate_call; val_call=validate_call(config=dict(arbitrary_types_allowed=True))

import yaml, json ,os, sys
from typing import Literal, Union, Tuple, List, get_args
from enum import Enum, EnumMeta

# should be annotated str that checks file, later...
file=str

try: # rich only acts on printout so its entirely options
    from rich.traceback import install, Traceback
    from rich.console import Console
    from rich.theme import Theme
    # Remove the padding that causes the extra left space
    custom_theme = Theme({
        "traceback.text": "",
        "traceback.exc_text": "",
    })

    console = Console(theme=custom_theme)
    install(
            suppress=[ 'pydantic', 'pydantic_core' ] ,
            extra_lines=1, # Extra lines around exception to be printed
            console=console,
            )
    # def last_only_hook(exc_type, exc, tb):
    #     exc.__cause__ = None    # removes the “from ex” inner traceback
    #     exc.__context__ = None  # removes implicit chained exceptions
    #     console.print(Traceback.from_exception(exc_type, exc, tb))

    # def last_frame_traceback(exc_type, exc, tb):
    #     # Walk to the last traceback frame
    #     while tb and tb.tb_next:
    #         tb = tb.tb_next

    #     # Clear any chaining to avoid extra blocks
    #     exc.__cause__ = None
    #     exc.__context__ = None

    #     # Render Rich traceback with only 1 frame
    #     tb_rich = Traceback.from_exception(
    #         exc_type,
    #         exc,
    #         tb,
    #         max_frames=1,     # show only last frame
    #         show_locals=False, # optional: hide local variables
    #         extra_lines=1,    # lines of source code around the error
    #     )
    #     console.print(tb_rich)

    # sys.excepthook = last_frame_traceback
except Exception as ex: 
    print(f"Could not install rich: {ex}")
