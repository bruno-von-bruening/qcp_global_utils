from pydantic import PrivateAttr,BaseModel, Field, validate_call; val_call=validate_call(config=dict(arbitrary_types_allowed=True))

import yaml, json ,os
from typing import Literal, Union, Tuple, List
from enum import Enum, EnumMeta

# should be annotated str that checks file, later...
file=str