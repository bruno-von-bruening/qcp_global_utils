from qcp_global_utils.util.import_helper import *
import re

from . import *
VERSION_EXPECTED_FORM_READABLE='[v]X.Y.Z[+<commit_hash>][.d<dirtyinfo>]'
# Why does this not match 0.1.1.dev23+g50eb2b584.d20260127?
# VERSION_EXPECTED_FORM
VERSION_1=r'v?(\d+)\.(\d+)(\.(\d+))?(?:\.dev\d+)?'
VERSION_EXPECTED_FORM = VERSION_1+r'(?:\+g?[0-9a-fA-F]+(?:\.d\d+)?)?'


from pydantic import BaseModel
class Version(BaseModel):
    major: int
    minor: int
    patch: int
    commit_hash: str = None
    dirty_info: str = None


@val_call
def get_version_hash(version_tag:str, package_name:str|None=None) -> str:

    assert re.fullmatch(VERSION_EXPECTED_FORM, version_tag), f"Cannot process version {version_tag} of package {package_name}. Expected format: {VERSION_EXPECTED_FORM_READABLE}"

    version_lead,*meta=version_tag.split('+')
    # analayse version lead should be like 0.1 or 0.1.1 etc
    assert re.fullmatch(VERSION_1, version_lead), f"Version lead should match {VERSION_1} ({version_lead})"
    # version_lead=version_lead.lstrip('v')
    # parts=version_lead.split('.')
    # if len(parts)==2:
    #     parts.append('0')  # patch=0 if not provided

    # for key, part in zip(['major','minor','patch'], parts):
    #     setattr(version_tag, key, int(part))
    if version_lead=='unknown':
        warn(f"{package_name}: provided unknown version, will use the main branch")
        return 'main'
    else:



        # Handle the meta
        if len(meta)<1:
            version=version
        else:
            if len(meta)>1:
                raise Exception(f"Cannot process version {version_tag}. Expected format: {VERSION_EXPECTED_FORM_READABLE} (meta is {meta})")
            version,*tags=meta[-1].split('.')
            if len(tags)>0:
                if len(tags)>1:
                    raise Exception(f"Cannot process version {version}. Expected format: {VERSION_EXPECTED_FORM_READABLE} (tags are {tags})")
                dirty=tags[0]
                assert re.match(r'd.*', dirty), f"Cannot process version {version}. Expected format: {VERSION_EXPECTED_FORM_READABLE} (found dirty tag {dirty})"
                warn(f"{package_name}: version {version} is dirty ({dirty}), please check if you should commit something!")

        # If hash comes from git, it starts with 'g' (that's what we expect since we work with git)
        # Notably the has may be longer since git truncates in app display to 7 chars
        assert version.startswith('g'), f"Version should come from git! Found {version} but should start with 'g'"
        version=version[1:]
        return version