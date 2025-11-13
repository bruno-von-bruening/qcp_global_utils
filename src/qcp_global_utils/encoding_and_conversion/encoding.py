from . import *
from .colors import col_di

PERIODIC_TABLE_STR = """
H                                                                                                                           He
Li  Be                                                                                                  B   C   N   O   F   Ne
Na  Mg                                                                                                  Al  Si  P   S   Cl  Ar
K   Ca  Sc                                                          Ti  V   Cr  Mn  Fe  Co  Ni  Cu  Zn  Ga  Ge  As  Se  Br  Kr
Rb  Sr  Y                                                           Zr  Nb  Mo  Tc  Ru  Rh  Pd  Ag  Cd  In  Sn  Sb  Te  I   Xe
Cs  Ba  La  Ce  Pr  Nd  Pm  Sm  Eu  Gd  Tb  Dy  Ho  Er  Tm  Yb  Lu  Hf  Ta  W   Re  Os  Ir  Pt  Au  Hg  Tl  Pb  Bi  Po  At  Rn
Fr  Ra  Ac  Th  Pa  U   Np  Pu  Am  Cm  Bk  Cf  Es  Fm  Md  No  Lr  Rf  Db  Sg  Bh  Hs  Mt  Ds  Rg  Cn  Nh  Fl  Mc  Lv  Ts  Og
"""

@validate_call
def nuclear_charge_to_element_symbol(Z: int =Field(ge=1)) -> str:
    """ Return atom type when given an atomic Number """
    atom_types=PERIODIC_TABLE_STR.split()
    Z_to_atty_di=dict([ (i+1, at_ty) for i, at_ty in enumerate(atom_types)])
    assert Z in Z_to_atty_di.keys(), f"Atom Charge \'{Z}\' cannot be associated to an known Element"
    return Z_to_atty_di[Z]
@validate_call
def element_symbol_to_nuclear_charge(at_ty: str) -> int:
    """ Return atom type when given an atomic Number """
    atom_types=PERIODIC_TABLE_STR.split()
    atty_to_Z_di=dict([ (at_ty,i+1) for i, at_ty in enumerate(atom_types)])
    assert at_ty in atty_to_Z_di.keys(), f"Atom type \'{at_ty}\' cannot be associated to a nuclear charge!"
    return atty_to_Z_di[at_ty]

def get_color(atom_type: int|str) -> Tuple[float, float, float]:
    if isinstance(atom_type, int): atom_type=nuclear_charge_to_element_symbol(atom_type)

    if not atom_type in col_di.keys():
        default_color=col_di['default']
        logging.warn(f"Do not know color for {atom_type}: ressorting to default: {default_color}")
        return default_color
    else:
        return col_di[atom_type]

@validate_call
def get_nshells_for_nuclear_charge(Z:int) -> int:
    ns=[ 2*(2*n+1) for n in range(10) ]
    # Encoding of table, 
    rows_di={ 1: [0], 2:[0,1], 3:[0,1], 4:[0,2,1], 5:[0,2,1], 6: [0,3,2,1], 7:[0,3,2,1] }
    row_range={}
    total_elements=0
    for k in rows_di.keys():
        new_elements=sum( ns[i] for i in rows_di[k] )
        row_range.update({k: [total_elements+1,total_elements+new_elements]})
        total_elements+=new_elements
        
    # Get the shell for given element (in which range is it included
    result=[]
    for k in row_range.keys():
        if Z in range(row_range[k][0], row_range[k][1]+1):
            result.append(k)
    if len(result)!=1:
        raise Exeption
    return result[0]
