import os

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import concurrent.futures
import multiprocessing
import shutil
import random
import time
import math as m
import numpy as np
import sys
import fractions

__PROJECT_ROOT__ = os.path.abspath(os.path.join(os.path.dirname(__file__),os.pardir))
sys.path.append(__PROJECT_ROOT__)

import choreo 

def main(the_i=0):
    

    # if (the_i != 0):
        
        # preprint_msg = str(the_i).zfill(2)+' : '

        # def print(*args, **kwargs):
            # """My custom print() function."""
            # builtins.print(preprint_msg,end='')
            # return builtins.print(*args, **kwargs)
            
    np.random.seed(int(time.time()*10000) % 5000)

    file_basename = ''

    Permutation_list = []
    Transform_list = []


    n_main_loop = 5
    n_ears = 3

    nbody = n_main_loop* (1 + n_ears)

    m_main_loop = 10.
    m_ears = 1.

    mass = np.array( [ (m_main_loop if i < n_main_loop else m_ears) for i in range(nbody)] , dtype=np.float64 )



    the_lcm = m.lcm(n_main_loop,n_ears)
    delta_i_main_loop = the_lcm//n_ears
    delta_i_ears = the_lcm//n_main_loop


    perm = np.zeros((nbody),dtype=int)
    for ibody in range(n_main_loop):
        perm[ibody] = ( (ibody+1) % n_main_loop) 

    for il in range(n_main_loop):
        for iear in range(n_ears):

            ibody = n_main_loop + il*n_ears +   iear
            jbody = n_main_loop + il*n_ears + ((iear + 1 ) % n_ears)

            perm[ibody] = jbody


    Permutation_list.append(perm)

    rot_angle = 2*np.pi * 0
    s = 1

    SpaceRot = np.array([[s*np.cos(rot_angle),-s*np.sin(rot_angle)],[np.sin(rot_angle),np.cos(rot_angle)]],dtype=np.float64)
    TimeRev = 1
    TimeShift=fractions.Fraction(numerator=1,denominator=the_lcm)

    Transform_list.append(
        choreo.ChoreoSym(
            SpaceRot=SpaceRot,
            TimeRev=TimeRev,
            TimeShift=TimeShift
        )
    )

    db = 1

    perm = np.zeros((nbody),dtype=int)
    for ibody in range(n_main_loop):
        perm[ibody] = ( (n_main_loop + db - ibody) % n_main_loop) 

    for il in range(n_main_loop):
        for iear in range(n_ears):

            ibody = n_main_loop + il*n_ears + iear
          
            jl = (n_main_loop + db - il) % n_main_loop
            jear = ( (n_ears     - iear) % n_ears)


            jbody = n_main_loop + jl*n_ears + jear

            perm[ibody] = jbody


    Permutation_list.append(perm)

    rot_angle = 2*np.pi * 0
    s = -1

    SpaceRot = np.array([[s*np.cos(rot_angle),-s*np.sin(rot_angle)],[np.sin(rot_angle),np.cos(rot_angle)]],dtype=np.float64)
    TimeRev = -1
    TimeShift=fractions.Fraction(numerator=0,denominator=1)

    Transform_list.append(
        choreo.ChoreoSym(
            SpaceRot=SpaceRot,
            TimeRev=TimeRev,
            TimeShift=TimeShift
        )
    )






    perm = np.zeros((nbody),dtype=int)
    for ibody in range(n_main_loop):
        perm[ibody] = ( (ibody+1) % n_main_loop) 

    for il in range(n_main_loop):
        for iear in range(n_ears):

            ibody = n_main_loop + il*n_ears + iear
            jbody = n_main_loop + ( (il+1) % n_main_loop) * n_ears + iear

            perm[ibody] = jbody


    Permutation_list.append(perm)

    rot_angle = 2*np.pi * 1./ n_main_loop
    s = 1

    SpaceRot = np.array([[s*np.cos(rot_angle),-s*np.sin(rot_angle)],[np.sin(rot_angle),np.cos(rot_angle)]],dtype=np.float64)
    TimeRev = 1
    TimeShift=fractions.Fraction(numerator=0,denominator=1)

    Transform_list.append(
        choreo.ChoreoSym(
            SpaceRot=SpaceRot,
            TimeRev=TimeRev,
            TimeShift=TimeShift
        )
    )











    # mass = np.ones((nbody),dtype=np.float64)

    Sym_list = choreo.MakeSymFromGlobalTransform(Transform_list,Permutation_list,mass=mass)




    # MomConsImposed = True
    MomConsImposed = False

    store_folder = os.path.join(__PROJECT_ROOT__,'Sniff_all_sym/')
    store_folder = store_folder+str(nbody)
    if not(os.path.isdir(store_folder)):
        os.makedirs(store_folder)

    Use_exact_Jacobian = True
    # Use_exact_Jacobian = False

    Look_for_duplicates = True
    # Look_for_duplicates = False

    Check_Escape = True
    # Check_Escape = False

    # Penalize_Escape = True
    Penalize_Escape = False

    save_first_init = False
    # save_first_init = True

    save_all_inits = False
    # save_all_inits = True

    Save_img = True
    # Save_img = False

    # Save_thumb = True
    Save_thumb = False

    # img_size = (12,12) # Image size in inches
    img_size = (8,8) # Image size in inches
    # thumb_size = (2,2) # Image size in inches
    thumb_size = (1,1) # Image size in inches


    
    # color = "body"
    color = "loop"
    # color = "velocity"
    # color = "all"

    Save_anim = True
    # Save_anim = False

    vid_size = (8,8) # Image size in inches
    # nint_plot_anim = 2*2*2*3*3*5*2
    nint_plot_anim = 600 * 4
    # nperiod_anim = 1./nbody
    # dnint = 32
    dnint = 4

    nint_plot_img = nint_plot_anim * dnint

    try:
        the_lcm
    except NameError:
        period_div = 1.
    else:
        period_div = the_lcm

    # nperiod_anim = 1.
    nperiod_anim = 1./period_div

    Plot_trace_anim = True
    # Plot_trace_anim = False

    # Save_Newton_Error = True
    Save_Newton_Error = False

    n_reconverge_it_max = 4
    # n_reconverge_it_max = 1

    # ncoeff_init = 102
    # ncoeff_init = 800
    # ncoeff_init = 201   
    # ncoeff_init = 512
    ncoeff_init = 1200
    # ncoeff_init = the_lcm
    
    disp_scipy_opt = False
    # disp_scipy_opt = True
    
    max_norm_on_entry = 1e20

    Newt_err_norm_max = 1e-12
    # Newt_err_norm_max_save = Newt_err_norm_max*1000
    Newt_err_norm_max_save = 1e-9

    duplicate_eps = 1e-8

    # krylov_method = 'lgmres'
    # krylov_method = 'gmres'
    krylov_method = 'bicgstab'
    # krylov_method = 'cgs'
    # krylov_method = 'minres'
    # krylov_method = 'tfqmr'


    # line_search = 'armijo'
    line_search = 'wolfe'
    
    gradtol_list =          [1e-1   ,1e-3   ,1e-5   ,1e-7   ,1e-9   ,1e-11  ,1e-13  ,1e-15  ]
    inner_maxiter_list =    [30     ,30     ,50     ,60     ,70     ,80     ,100    ,100    ]
    maxiter_list =          [100    ,1000   ,1000   ,1000   ,500    ,500    ,300    ,100    ]
    outer_k_list =          [5      ,5      ,5      ,5      ,5      ,7      ,7      ,7      ]
    store_outer_Av_list =   [False  ,False  ,False  ,False  ,False  ,True   ,True   ,True   ]
    
    n_optim_param = len(gradtol_list)
    
    gradtol_max = 100*gradtol_list[n_optim_param-1]
    # foundsol_tol = 1000*gradtol_list[0]
    foundsol_tol = 1e10

    escape_fac = 1e0
    escape_min_dist = 1
    escape_pow = 2.0

    n_grad_change = 1.
    # n_grad_change = 1.5

    coeff_ampl_o=3e-2
    # coeff_ampl_o=1e0
    k_infl=0
    # k_max=600
    k_max=200
    # k_max=200
    coeff_ampl_min=1e-16

    freq_erase_dict = 100
    hash_dict = {}

    n_opt = 0
    # n_opt_max = 1
    # n_opt_max = 5
    n_opt_max = 1e10
    # n_opt_max = 0

    # n_find_max = 1
    n_find_max = 1e10
    
    mul_coarse_to_fine = 3

    # Save_All_Coeffs = True
    Save_All_Coeffs = False

    # Save_Init_Pos_Vel_Sol = True
    Save_Init_Pos_Vel_Sol = False

    n_save_pos = 'auto'
    Save_All_Pos = True
    # Save_All_Pos = False

    plot_extend = 0.03

    # all_kwargs = choreo.Pick_Named_Args_From_Dict(choreo.Find_Choreo,dict(globals(),**locals()))
    # choreo.Find_Choreo(**all_kwargs)

    all_kwargs = choreo.Pick_Named_Args_From_Dict(choreo.GenSymExample,dict(globals(),**locals()))
    choreo.GenSymExample(**all_kwargs)



# if __name__ == "__main__":
#     main(0)
   

if __name__ == "__main__":

    n = multiprocessing.cpu_count()
    # n = multiprocessing.cpu_count()//2
    # n = 10
    
    print(f"Executing with {n} workers")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=n) as executor:
        
        res = []
        for i in range(1,n+1):
            res.append(executor.submit(main,i))
            time.sleep(0.01)
# 
 
