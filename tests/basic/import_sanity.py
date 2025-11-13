#raise NotImplementedError(f"Would like to import all .py files from module to check that there are no typos, etc., but\
#do not know hot to do that")
import pkgutil
import os
import qcp_global_utils
import importlib

pkg_toplevel= os.path.dirname(qcp_global_utils.__file__) 
content=os.walk(pkg_toplevel)
failures=dict()

for root, dirs, files in content:
    python_files=[ f for f in files if f.lower().endswith('.py') ]
    
    for fi in python_files:
        subdirs=os.path.relpath(root,pkg_toplevel ).strip('/').split('/')
        subdirs=[s for s in subdirs if s!='.']
        module_name='.'.join( ['qcp_global_utils']+subdirs+ [
                             fi])
        assert module_name.endswith('.py')
        module_name=module_name[:-3]
        if module_name.endswith('__init__'): 
            module_name=module_name.replace('.__init__','')


        try:
            importlib.import_module(module_name)
        except Exception as ex:
            assert module_name not in failures.keys()
            failures.update({module_name: str(ex)})

if len(failures)==0: print(f"all import are fine!")
else: 
    print(f"Found {len(failures)} problems in import:\n"
          +'\n'.join([
              '    '+f"{k}: {v}"
              for k,v in failures.items()
              ])
    )



