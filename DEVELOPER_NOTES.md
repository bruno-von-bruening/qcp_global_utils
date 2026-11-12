$PSI4_EXE does not get processed.
I could just have a process or cycle options that drop the file and then reads in (to process like input is processed through init)

# How does the qcp_export_envo work
Prepare
1. SHould setup version dynamically with setuptool-scm (have a look at e.g. qcp/density_operations)
2.  copy qcp_export_envo.py and add it to source (look again e.g. at qcp/density_operations)
    Define the package name and the custom pip dependencies

Then follow the steps:
1. Just run test/make sure the stuff is running/using right dependencies
2. run qcp_export_envo.py -f <the old envo file> (this will update dependencies)
3. if dirty make a commit and pip install to current envo!
3. vimdiff (v -d ) and adopt the changes!
