# v0.1

## v0.1.01 
    reading sqlmodel instances for qcAPI

## v0.1.02 Created input file parser machinery, various technical changes
Change installer routine from script based to pip package based. Installation is done through ```qcp_installer```
package.

Added default inclusion of positional and keyword arguments options to ```run_shell_command``` function.
Just convenience.

Added parser class, that can be used for portable input files in yaml format. Gets powerful with type validation through
pydantic package.

Created new utils directory in package. At the moment just used to standardise repretitive imports through
```import_helper.py``` content.

Copied get_nshell function form encoding_and_conversion.encoding (previously in my old modules path)

# v0.1.03 Minor Modifications to controller_model
Mainly add convenience functionality to controller_model

# v0.1.04 Parser model: placeholder and enum
Added processing of Enums to parser model and method for generation of placeholder string

# v0.1.04a Minor Patch
No warning if multiple controll models are found wihtin Union.
New file for get environment variable function. 