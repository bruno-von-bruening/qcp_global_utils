#!/bin/env python 

import shutil
from typing import Tuple
import time
import os
import csv

def get_storage_usage(directory: str) -> Tuple[int, int]:
    """
    Returns (used_bytes, free_bytes) for the filesystem containing `directory`.
    """
    usage = shutil.disk_usage(directory)
    return usage.used, usage.free


def append_timings(entry, storage_info):
    with open(storage_info, 'a') as wr:
        wr.write(','.join(map(str, entry))+'\n')

def save_max(the_list, storage_info):
    """ Appends the max to the file """
    if len(the_list)==0:
        return
    the_max=sorted(the_list, key=lambda x: x[0], reverse=True)[0]
    entry=(time.time(), *the_max)
    append_timings(entry, storage_info)

def initialize_file(directory):
    """ Plan is to continously append, make first line in csv for hings"""
    storage_info='storage_info.csv'
    def init_file(directory):
         comment=f"# This host: {os.uname().nodename}, directory: {directory}\n"
         with open(storage_info, 'w') as wr:
            wr.write(comment)
            wr.write('timestamp,used_bytes,free_bytes\n')
    if not os.path.isfile(storage_info):
        init_file(directory)
    else: # tell user it allready exists and for conformation
        with open(storage_info) as f:
            lines=f.readlines()
            print(f"File {storage_info} already exists.")
            print(f"First lines of the file:\n"+'\n'.join(['    '+x.strip('\n') for x in lines[:min(5,len(lines))]]))
            print(f"Do you want to:\n"+'\n'.join([f"{i+1}: {text} ({opt})" for i,(text,opt) 
                                                  in enumerate(zip(
                                                      ["append to it?","overwrite it?"],
                                                      ["y","o"]
                            ))]))
        answer=input().lower()
        if answer not in ['y', 'yes', 'o', 'overwrite']:
            print("Exiting.")
            exit(0)
        elif answer in ['o', 'overwrite']:
            init_file(directory)
    return storage_info

def bytes_to_gb(bytes):
    return bytes / (1024**3)


def get_max_space(storage_info):
    with open(storage_info, newline='') as f:
        reader = csv.reader(f)
        # Skip comment/header lines
        for row in reader:
            if not row or row[0].startswith('#') or row[0] == 'timestamp':
                continue
            used_bytes = float(row[1])
            yield used_bytes

def max_used_bytes(storage_info):
    return max(get_max_space(storage_info), default=0)

def track_timing(directory: str, sleep_time: int, agg_intervals: int):
    """ Starts a continous process"""
    
    # Drop the information under a file
    storage_file=initialize_file(directory)

    cnt=0
    while True:
        current_list=[]
        try:
            for i in range(agg_intervals):
                time.sleep(sleep_time)
                used, free = get_storage_usage(directory)
                current_list+=[ (used, free)]
        except KeyboardInterrupt:
            print("Stopping tracking."); break
        except Exception as e:
            print(f"An error occurred: {str(e)}") ; break
        finally:
            save_max(current_list, storage_file)
        try:
            if cnt%10==0:
                time.sleep(.5)
                print(f"Max space used: {bytes_to_gb(max_used_bytes(storage_file))} GB")
        except Exception as e:
            print(f"Could not read max space: {str(e)}")
        cnt+=1


if __name__ == "__main__":
    description=None
    epilog=None
    import argparse as ap
    par=ap.ArgumentParser(description=description, epilog=epilog, formatter_class=ap.RawDescriptionHelpFormatter)
    add=par.add_argument
    add( 'directory', type=str, default='.',
        help="Directory to check storage usage for (default: current directory)."
    )
    add( '--intervals', '-i', type=int, default=12,
        help="Number of intervals to check before saving the maximum (default: 12)."
    )
    add( '--refresh', '-r', type=int, default=5,
        help="Time in seconds between each check (default: 5)."
    )
    args=par.parse_args()
    directory=args.directory

    sleep_time=args.refresh
    agg_intervals=args.intervals

    track_timing(directory, sleep_time, agg_intervals)