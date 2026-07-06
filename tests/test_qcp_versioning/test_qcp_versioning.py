from qcp_versioning.helper import Version

dummy_var='0.1.dev188+g15f3765d8.d20260331'
var_agrees=['0.1.dev188+g15f3765d8.d20260332']
var_disagrees=['0.2.dev188+g15f3765d8.d20260332']

def test_init_version_class():
    try:
        ver=Version(dummy_var)
        rec=ver.string
        assert ver.string==dummy_var, f"Failed to recompose whole version string: {rec} vs {ver}"
    except Exception as ex:
        raise Exception(f"Could not process {dummy_var}: {str(ex)}") from ex
def test_compare_version():
    for v in var_agrees:
        dis= Version(dummy_var).disagreements( Version(v) )
        assert len(dis)==0, dis
    for v in var_disagrees:
        dis=Version(dummy_var).disagreements( Version(v) )
        assert len(dis)>0, (dummy_var,v)
