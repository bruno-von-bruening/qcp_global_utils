from qcp_global_utils.util.import_helper import *
import re

from . import *
VERSION_EXPECTED_FORM_READABLE='[v]X.Y.Z[+<commit_hash>][.d<dirtyinfo>]'
# Why does this not match 0.1.1.dev23+g50eb2b584.d20260127?
# VERSION_EXPECTED_FORM
VERSION_1=r'v?(\d+)\.(\d+)(\.(\d+))?(?:\.dev\d+)?'
VERSION_EXPECTED_FORM = VERSION_1+r'(?:\+g?[0-9a-fA-F]+(?:\.d\d+)?)?'


from pydantic import BaseModel

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
def check_version(version_tag):
    assert re.fullmatch(VERSION_EXPECTED_FORM, version_tag), f"Cannot process version {version_tag} of package {package_name}. Expected format: {VERSION_EXPECTED_FORM_READABLE}"

class Version(BaseModel):
    major: int
    minor: int
    patch: int|None=None # could be dev[i]
    dev: int|None=None # could be dev[i]
    commit_hash: str = None
    dirty_info: int|str = None
    dirty_date: Tuple[int,int,int]=None
    @property
    def string(self):
        kw=self.model_dump()
        ver_tag='.'.join([str(x) for x in [self.major,self.minor,self.patch] if x is not None])
        if self.dev is not None: ver_tag+=f".dev{self.dev}"
        date=kw['dirty_date']
        date=f"{date[0]:02d}{date[1]:02d}{date[2]}"
        return  ver_tag+ f"+g{kw['commit_hash']}d{kw['dirty_info']}.d{date}"
class Version(Version):
    def __init__(self,*args,**kwargs):
        if len(args)==1:
            assert len(kwargs)==0, f"Both kwargs and args provided"
            new_kwargs=dict()
            ver=args[0]
            assert isinstance(ver,str), f"Not a string {ver}"
            check_version(ver)
            try:
                version_int,dirties=ver.split('+')
                tag=f".dev"
                version_int,*rest =version_int.split(tag)
                if len(rest)==1:
                    new_kwargs.update(dev=int(rest[0]))
                elif len(rest)>1: raise Exception(f"More than one dev tag!: {ver}")
                tags=['major','minor','patch']
                vv=version_int.split('.')
                new_kwargs.update( dict([ 
                                         (k,int(v)) for k,v in zip(tags,vv)
                ]))

                git_tag,date_tag=dirties.split('.')

                git_tag,*dirty_v=git_tag.split('d')
                if len(dirty_v)==1:
                    new_kwargs['dirty_info']=dirty_v[0]
                elif len(dirty_v)>1: raise Exception(f"Multiple dirty tags found: {dirty_v}")

                new_kwargs['commit_hash']=git_tag[1:]
                new_kwargs['dirty_date']=(float(date_tag[1:5]),float(date_tag[5:7]), float(date_tag[7:9]) )

            except Exception as ex:
                raise Exception(f"Problem in processing {ver}: {str(ex)}") from ex
            kwargs=new_kwargs

        elif len(args)>1: raise Exception(f"Expected none or one positional argument got {len(args)}")
        super().__init__(**kwargs)
    def disagreements(self, other_version:Version):
        this, other= [ x.model_dump() for x in [self, other_version] ]
        non_critical=['dirty_date']
        disagreements=dict()
        for k,v1 in [ (k,v) for  k,v in this.items() if k not in non_critical ]:
            v2=other[k]
            if v1!=v2:
                disagreements.update({k:(v1,v2)})
        return disagreements




