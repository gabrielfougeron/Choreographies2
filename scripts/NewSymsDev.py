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
        '3q',
        '3q3q',
        '3q3qD',
        '2q2q',
        '4q4q',
        '4q4qD',
        '4q4qD3k',
        '1q2q',
        '5q5q',
        '6q6q',
        '2C3C',
        '2D3D',   
        '2C3C5k',
        '2D3D5k',
        '2D1',
        '4C5k',
        '4D3k',
        '4C',
        '4D',
        '3C',
        '3D',
        '3D1',
        '3C2k',
        '3D2k',
        '3Dp',
        '3C4k',
        '3D4k',
        '3C5k',
        '3D5k',
        '3C101k',
        '3D101k',
        'test_3D5k',
        '3C7k2',
        '3D7k2',
        '6C',
        '6D',
        '6Ck5',
        '6Dk5',
        '5Dq',
        '2C3C5C',
        '3C_3dim',
        '2D1_3dim', 
        '3C11k',
        '5q',
        '5Dq_',
        'uneven_nnpr',
        '3C4q4k',
        '3D4q4k',
        '2D2D',
        '2D2D5k',
        '2D1D1D',
        '1Dx3',
        '1D1D1D',
        '3DD',
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

def ortho_err_l(mat):
    m,n = mat.shape
    mat2 = np.matmul(mat.conj().T,mat)
    return np.linalg.norm(mat2 - np.identity(n))
                          
def ortho_err_r(mat):
    m,n = mat.shape
    mat2 = np.matmul(mat,mat.conj().T)
    return np.linalg.norm(mat2 - np.identity(m))
                          

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

    NBS.nint_fac = 2
    params_buf = np.random.random(NBS.nparams)
    all_coeffs = NBS.params_to_all_coeffs_noopt(params_buf)        
    params_pos = NBS.params_changevar(params_buf)

    for il in range(NBS.nloop):
        print()
        print(f'{il = }')
        params_basis = NBS.params_basis_pos(il)
        
        params_basis_r = np.empty((params_basis.shape[0],params_basis.shape[1],params_basis.shape[2],2),dtype=np.float64)
        
        params_basis_r[:,:,:,0] = params_basis.real
        params_basis_r[:,:,:,1] = params_basis.imag
        
        m = params_basis.shape[0]
        n = params_basis.shape[1]*params_basis.shape[2]*2
        
        params_basis_r = params_basis_r.reshape(m, n)
        
        nn = n*m
        
        nz = 0
        nu = 0
        for i in range(m):
            for j in range(n):
                if abs(params_basis_r[i,j]) < eps:
                    nz += 1
                
                elif abs(abs(params_basis_r[i,j])-1) < eps:
                    nu +=1
                    
        nnz_k = NBS.nnz_k(il)

        all_coeffs_loop = all_coeffs[il,:,:]
        
        ncoeffs_loop = all_coeffs_loop.shape[0]
        ncoeff_min_loop = NBS.ncoeff_min_loop[il]
        nc = ncoeffs_loop//ncoeff_min_loop
        
        params_loop = params_pos[2*NBS.params_shifts[il]:NBS.params_shifts[il]+NBS.params_shifts[il+1]].reshape(-1,geodim,2)

        if nnz_k.shape[0] == 1:
            if nnz_k[0] == 0:
                
                print(f'{nnz_k = }')
                
                params_basis = NBS.params_basis_pos(il)
                
                m = params_basis.shape[0]
                n = params_basis.shape[2]
                 
                if 2*m == n:
                    
                    params_basis_r = np.empty((m,2, n),dtype=np.float64)

                    params_basis_r[:,0,:] = params_basis[:,0,:].real
                    params_basis_r[:,1,:] = params_basis[:,0,:].imag
                    
                    if np.linalg.norm(params_basis_r.reshape(n,n) - np.identity(params_basis.shape[2])) < eps:
                        
                        print("Identity transformation")

                        assert np.linalg.norm(all_coeffs_loop[0:-1:ncoeff_min_loop,:] - params_loop[:,:,0] - params_loop[:,:,1] * 1j ) < eps
        
        
        # 
        # print(nc)
        # for i in range(min(nc, params_loop.shape[0])):
        #     
        #     print(np.linalg.norm(all_coeffs_loop[ncoeff_min_loop*i,:].real - params_loop[i,:,0])+np.linalg.norm(all_coeffs_loop[ncoeff_min_loop*i,:].imag - params_loop[i,:,1]))
        #     
        #     assert np.linalg.norm(all_coeffs_loop[ncoeff_min_loop*i,:].real - params_loop[i,:,0])+np.linalg.norm(all_coeffs_loop[ncoeff_min_loop*i,:].imag - params_loop[i,:,1]) < eps
        
        
        # print(all_coeffs_flat.real[:-2] )
        # print(params_loop[::2])
        # print(all_coeffs_flat.imag[:-2] )
        # print(params_loop[1::2])
        # # 
        
        # print(np.linalg.norm(all_coeffs_flat.real[:-2] - params_loop[::2]))
        # print(np.linalg.norm(all_coeffs_flat.imag[:-2] - params_loop[1::2]))
        
    # all_pos = scipy.fft.irfft(all_coeffs, axis=1, norm='forward')
    

















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
