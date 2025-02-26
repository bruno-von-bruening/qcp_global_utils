#!/usr/bin/env
import os, yaml
import subprocess as sp

home=os.path.realpath('..')

def setup_env_vars():
    env={'QC_GLOBAL_UTILITIES_HOME':home}
    return env

def  env_setup_instructions(env):
    instructions=[
        f"export {k}=\"{v}\""
        for k, v in env.items()
    ]
    with open('add_to_shell_init.txt','w') as wr:
        wr.write('\n'+'\n'.join(['# paths for Densityb Operations pip module']+instructions)+'\n\n')

    indent=4*' '
    instructions='\n'.join([f"Add the following commands to your shell initialization:"]+[ indent +x for x in instructions])

    # COuld also be done by just runnig cat and appending to right script
    print(instructions)

def setup():

    env=setup_env_vars()
    env_setup_instructions(env)

if __name__=='__main__':
    setup()
