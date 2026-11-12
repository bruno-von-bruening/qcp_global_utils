try:
    # THis will work for python 3.11 and higher
    from contextlib import chdir
except:
    # This will also work for python <3.11
    import os
    from contextlib import contextmanager

    @contextmanager
    def chdir(path):
        previous_dir = os.getcwd()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(previous_dir)
