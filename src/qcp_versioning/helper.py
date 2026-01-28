
VERSION_EXPECTED_FORM_READABLE=r'[v]X.Y.Z[+<commit_hash>][.d<dirtyinfo>]'
# Why does this not match 0.1.1.dev23+g50eb2b584.d20260127?
# VERSION_EXPECTED_FORM
VERSION_EXPECTED_FORM=r'[v]?\d+\.\d+\.\d+(\.[a-zA-Z0-9]+)?(\+.[a-f0-9]+)?(\.d[0-9]+)?'