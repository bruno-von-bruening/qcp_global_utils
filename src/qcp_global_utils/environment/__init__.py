from qcp_global_utils.pydantic.pydantic import pdtc_file, directory
from pydantic import validate_call, BaseModel; val_call=validate_call(config=dict(arbitary_types_allowed=True))
from typing import Literal, Tuple, List

import os, json, yaml

from enum import Enum