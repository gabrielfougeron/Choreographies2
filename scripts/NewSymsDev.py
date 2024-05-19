import os
import sys
__PROJECT_ROOT__ = os.path.abspath(os.path.join(os.path.dirname(__file__),os.pardir))
sys.path.append(__PROJECT_ROOT__)

import choreo 
import time
import pyquickbench
import json
import numpy as np
import scipy
import itertools

np.set_printoptions(
    precision = 3,
    edgeitems = 10,
    # linewidth = 150,
    linewidth = 300,
    floatmode = "fixed",
)


def proj_to_zero(array, eps=1e-14):
    for idx in itertools.product(*[range(i)  for i in array.shape]):
        if abs(array[idx]) < eps:
            array[idx] = 0.

def main():
        
    all_tests = [
        # '3q',
        # '3q3q',
        # '3q3qD',
        # '2q2q',
        # '4q4q',
        # '4q4qD',
        # '4q4qD3k',
        # '1q2q',
        # '5q5q',
        # '6q6q',
        '2C3C',
        # '2D3D',   
        # '2C3C5k',
        # '2D3D5k',
        # '2D1',
        # '4C5k',
        # '4D3k',
        '4C',
        # '4D',
        '3C',
        # '3D',
        # '3D1',
        # '3C2k',
        # '3D2k',
        # '3Dp',
        # '3C4k',
        # '3D4k',
        # '3C5k',
        # '3D5k',
        # '3C101k',
        # '3D101k',
        # 'test_3D5k',
        # '3C7k2',
        # '3D7k2',
        '6C',
        # '6D',
        # '6Ck5',
        # '6Dk5',
        # '5Dq',
        # '2C3C5C',
        # '3C_3dim',
        # '2D1_3dim', 
        # '3C11k',
        # '5q',
        # '5Dq_',
        # 'uneven_nnpr',
        # '3C4q4k',
        # '3D4q4k',
        # '2D2D',
        # '2D2D5k',
        # '2D1D1D',
        # '1Dx3',
        # '1D1D1D',
        # '3DD',
    ]

    TT = pyquickbench.TimeTrain(
        include_locs = False    ,
        align_toc_names = True  ,
    )

    for test in all_tests:
        print()
        # print("  OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO  ")
        print()
        print(test)
        # print()


        doit(test)
        
        TT.toc(test)

    print()
    print(TT)
  

def proj_to_zero(array, eps=1e-14):
    for idx in itertools.product(*[range(i)  for i in array.shape]):
        if abs(array[idx]) < eps:
            array[idx] = 0.


def doit(config_name):
        
    eps = 1e-10

    Workspace_folder = os.path.join(__PROJECT_ROOT__, 'tests', 'NewSym_data', config_name)
    params_filename = os.path.join(Workspace_folder, 'choreo_config.json')
    
    with open(params_filename) as jsonFile:
        params_dict = json.load(jsonFile)

    all_kwargs = choreo.find.ChoreoLoadFromDict(params_dict, Workspace_folder, args_list=["geodim", "nbody", "mass", "charge", "inter_pow", "inter_pm", "Sym_list"])
    
    geodim = all_kwargs["geodim"]
    nbody = all_kwargs["nbody"]
    mass = all_kwargs["mass"]
    charge = all_kwargs["charge"]
    Sym_list = all_kwargs["Sym_list"]
    
    inter_pow = all_kwargs["inter_pow"]
    inter_pm = all_kwargs["inter_pm"]
    
    inter_pm = -1
    
    if (inter_pow == -1.) and (inter_pm == 1) :
        inter_law = scipy.LowLevelCallable.from_cython(choreo.cython._NBodySyst, "gravity_pot")
    else:
        inter_law = choreo.numba_funs_new.pow_inter_law(inter_pow/2, inter_pm)

    NBS = choreo.cython._NBodySyst.NBodySyst(geodim, nbody, mass, charge, Sym_list, inter_law)


    NBS.nint_fac = 10000
    
    coeff_ampl_o = 1.
    k_infl = 3
    k_max = 30
    coeff_ampl_min = 1e-16
    
    x_min, x_max = NBS.Make_params_bounds(coeff_ampl_o, k_infl, k_max, coeff_ampl_min)
    x_ptp = x_max - x_min
    x_avg = (x_min + x_min) / 2
    
    params_buf = x_avg + x_ptp * np.random.random((NBS.nparams))
    

    # Unoptimized version
    all_coeffs = NBS.params_to_all_coeffs_noopt(params_buf)        
    kin_tot = NBS.all_coeffs_to_kin_nrg(all_coeffs)
    # print(kin_tot)
    
    all_pos = scipy.fft.irfft(all_coeffs, axis=1, norm='forward')
# 
#     print(all_coeffs.dtype)
#     print(all_coeffs.shape)
#     print(NBS.nloop)
#     print(NBS.ncoeffs)
#     print(NBS.geodim)
    
    NBS.all_coeffs_pos_to_vel_inplace(all_coeffs)
    all_vel = scipy.fft.irfft(all_coeffs, axis=1, norm='forward')
    
    # print(all_vel.shape)
    # print(NBS.nint)
    # 
    vel_int = np.sum(all_vel*all_vel.conj(), axis=(1,2)) / NBS.nint
    kin_tot_noopt = 0
    for il in range(NBS.nloop):
        kin_tot_noopt += vel_int[il] * NBS.loopmass[il]*NBS.loopnb[il] * 0.25

    # print(kin_tot_noopt)
    # print(kin_tot - kin_tot_noopt)
    # print(kin_tot / kin_tot_noopt)
    
    assert abs(kin_tot - kin_tot_noopt) < eps
    


    segmvel_cy = NBS.params_to_segmvel(params_buf)
    segmpos_cy = NBS.params_to_segmpos(params_buf)
    

    NBS.segm_to_path_stats(segmpos_cy, segmvel_cy)
    
    print(f'{NBS.nint_min = }')


    nparam_nosym = geodim * NBS.nint * nbody
    nparam_tot = NBS.nparams_incl_o // 2

    print('*****************************************')
    print('')
    print()
    print(f"total binary segment interaction count: {NBS.nbin_segm_tot}")
    print(f"unique binary segment interaction count: {NBS.nbin_segm_unique}")
    print(f'{NBS.nsegm = }')
    print(f"ratio of total to unique binary interactions : {NBS.nbin_segm_tot  / NBS.nbin_segm_unique}")
    print(f'ratio of integration intervals to segments : {(nbody * NBS.nint_min) / NBS.nsegm}')
    print(f"ratio of parameters before and after constraints: {nparam_nosym / nparam_tot}")

    reduction_ratio = nparam_nosym / nparam_tot

    assert abs((nparam_nosym / nparam_tot)  - reduction_ratio) < eps
    

#     # return
# 
#     filename = os.path.join(Workspace_folder, config_name+'_graph_segm.pdf')
#     choreo.cython._NBodySyst.PlotTimeBodyGraph(NBS.SegmGraph, nbody, NBS.nint_min, filename)





























if __name__ == "__main__":
    main()
