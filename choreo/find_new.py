import sys
import os
try:
    import concurrent.futures
except:
    pass

import numpy as np
import scipy
import json
import time
import inspect
import threadpoolctl

import choreo.metadata
import choreo.scipy_plus
from choreo.cython._ActionSym import ActionSym

def Find_Choreo(
    *,
    geodim,
    nbody,
    mass,
    charge,
    inter_pow,
    inter_pm,
    Sym_list,
    nint_fac_init,
    coeff_ampl_o,
    k_infl,
    k_max,
    coeff_ampl_min,
    n_opt_max,
    n_find_max,
    save_first_init,
    Look_for_duplicates,
    Duplicates_Hash,
    store_folder,
    freq_erase_dict,
    ReconvergeSol,
    LookForTarget,
    save_all_inits,
    file_basename,
    AddNumberToOutputName,
    Save_img,
    Save_thumb,
    Save_anim,
    callback_after_init_list,
    optim_callback_list,
    max_norm_on_entry,
    gradtol_list,
    inner_maxiter_list,
    maxiter_list,
    outer_k_list,
    store_outer_Av_list,
    n_optim_param,
    krylov_method,
    Use_exact_Jacobian,
    disp_scipy_opt,
    line_search,
    linesearch_smin,
    Check_Escape,
    gradtol_max,
    n_reconverge_it_max,
    plot_extend,
    mul_coarse_to_fine,
    duplicate_eps,
    Save_SegmPos,
    img_size,
    thumb_size,
    color,
    color_list,
    fftw_planner_effort,
    fftw_wisdom_only,
    fftw_nthreads,
    fft_backend,
):
    """

    Finds periodic solutions

    """

    if (inter_pow == -1.) and (inter_pm == 1) :
        inter_law = scipy.LowLevelCallable.from_cython(choreo.cython._NBodySyst, "gravity_pot")
    else:
        inter_law = choreo.numba_funs_new.pow_inter_law(inter_pow/2, inter_pm)

    NBS = choreo.cython._NBodySyst.NBodySyst(geodim, nbody, mass, charge, Sym_list, inter_law)

    NBS.fftw_planner_effort = fftw_planner_effort
    NBS.fftw_wisdom_only = fftw_wisdom_only
    NBS.fftw_nthreads = fftw_nthreads
    NBS.fft_backend = fft_backend

    NBS.nint_fac = nint_fac_init
       
    nparam_nosym = NBS.geodim * NBS.nint * NBS.nbody
    nparam_tot = NBS.nparams_incl_o // 2

    print('System is composed of:')
    print(f'    {NBS.nbody:d} bodies')
    print(f'    {NBS.nloop:d} independent loops')
    print(f'    {NBS.nint_min:d} integration segments')
    print(f'    {NBS.nsegm:d} independent generating segments')
    print(f'    {NBS.nbin_segm_unique:d} binary interactions between segments')
    print()
    print(f'The number of free parameters is reduced by a factor of {nparam_nosym / nparam_tot}')
    print(f'The number of independent interactions is reduced by a factor of {NBS.nbin_segm_tot  / NBS.nbin_segm_unique}')
    print(f'The number of independent segments is reduced by a factor of {(nbody * NBS.nint_min) / NBS.nsegm}')
    print()

    x_min, x_max = NBS.Make_params_bounds(coeff_ampl_o, k_infl, k_max, coeff_ampl_min)
    x_ptp = x_max - x_min
    x_avg = (x_min + x_min) / 2
    
    del x_min, x_max

#     if not(SkipCheckRandomMinDist):
# 
#         x0 = np.random.random(ActionSyst.nparams)
#         xmin = ActionSyst.Compute_MinDist(x0)
#         if (xmin < 1e-5):
#             print("")
#             print(f"Init minimum inter body distance too low: {xmin}")
#             print("There is likely something wrong with constraints.")
#             print("")
# 
#             n_opt_max = -1

    n_opt = 0
    n_find = 0

    if optim_callback_list is None:
        optim_callback_list = []
    
    n_optim_callback_list = len(optim_callback_list)    

    if callback_after_init_list is None:
        callback_after_init_list = []
    n_callback_after_init_list = len(callback_after_init_list)
    
    ForceFirstEntry = save_first_init
    
    hash_dict = {}
    action_dict = {}

    while (((n_opt < n_opt_max) and (n_find < n_find_max)) or ForceFirstEntry):
        
        NBS.nint_fac = nint_fac_init

        ForceFirstEntry = False
        AskedForNext = False

        if (Look_for_duplicates and ((n_opt % freq_erase_dict) == 0)):

            hash_dict = {}
            action_dict = {}
            UpdateHashDict(store_folder, hash_dict, action_dict)

        if (ReconvergeSol):
            raise NotImplementedError

            # x_avg = ActionSyst.Package_all_coeffs(all_coeffs_init)
        
        elif (LookForTarget):
            raise NotImplementedError

            # all_coeffs_avg = ActionSyst.Gen_init_avg_2D(nT_slow,nT_fast,Info_dict_slow,all_coeffs_slow,Info_dict_fast_list,all_coeffs_fast_list,il_slow_source,ibl_slow_source,il_fast_source,ibl_fast_source,Rotate_fast_with_slow,Optimize_Init,Randomize_Fast_Init)

            # x_avg = ActionSyst.Package_all_coeffs(all_coeffs_avg)
        else:
            pass

        x = x_avg + x_ptp * np.random.random((NBS.nparams))
        
        segmpos = NBS.params_to_segmpos(x)
        
        if save_all_inits or (save_first_init and n_opt == 0):

            max_num_file = 0
            
            for filename in os.listdir(store_folder):
                file_path = os.path.join(store_folder, filename)
                file_root, file_ext = os.path.splitext(os.path.basename(file_path))
                
                if (file_basename in file_root) and (file_ext == '.json' ):

                    file_root = file_root.replace(file_basename,"")

                    try:
                        max_num_file = max(max_num_file,int(file_root))
                    except:
                        pass

            max_num_file = max_num_file + 1

            if (AddNumberToOutputName):   
                filename_output = os.path.join(store_folder,file_basename+'_init_'+str(max_num_file).zfill(5))

            else:
                filename_output = os.path.join(store_folder,file_basename+'init')

            NBS.Write_Descriptor(x, segmpos=segmpos, filename = filename_output+'.json')

            if Save_img :
                NBS.plot_segmpos_2D(segmpos, filename_output+'.png', fig_size=img_size, color=color, color_list=color_list)     

            if Save_thumb :
                NBS.plot_segmpos_2D(segmpos, filename_output+'_thumb.png', fig_size=thumb_size, color=color, color_list=color_list)     
                
            if Save_SegmPos:
                np.save(filename_output+'.npy', segmpos)

        for i in range(n_callback_after_init_list):
            callback_after_init_list[i]()

        f0 = NBS.segmpos_params_to_action_grad(segmpos, x)
        best_sol = choreo.scipy_plus.nonlin.current_best(x, f0)

        GoOn = (best_sol.f_norm < max_norm_on_entry)
        
        if not(best_sol.f_norm < max_norm_on_entry):
            print(f"Norm on entry is {best_sol.f_norm:.2e} which is too big.")
        
        i_optim_param = 0
        current_cvg_lvl = 0 
        n_opt += 1
        
        GoOn = GoOn and (n_opt <= n_opt_max)
        
        if (n_opt <= n_opt_max):
            print(f'Optimization attempt number: {n_opt}')
        # else:
        #     print('Reached max number of optimization attempts')

        while GoOn:
            # Set correct optim params

            x = np.copy(best_sol.x)
            
            inner_tol = 0.
            
            rdiff = None
            gradtol = gradtol_list[i_optim_param]
            inner_maxiter = inner_maxiter_list[i_optim_param]
            maxiter = maxiter_list[i_optim_param]
            outer_k = outer_k_list[i_optim_param]
            store_outer_Av = store_outer_Av_list[i_optim_param]

            ActionGradNormEnterLoop = best_sol.f_norm
            
            print(f'Action Grad Norm on entry: {ActionGradNormEnterLoop:.2e}')
            print(f'Optim level: {i_optim_param+1} / {n_optim_param}    Resize level: {current_cvg_lvl+1} / {n_reconverge_it_max+1}')
            
            inner_M = None

            if (krylov_method == 'lgmres'):
                jac_options = {'method':krylov_method,'rdiff':rdiff,'outer_k':outer_k,'inner_inner_m':inner_maxiter,'inner_store_outer_Av':store_outer_Av,'inner_tol':inner_tol,'inner_M':inner_M }
            elif (krylov_method == 'gmres'):
                jac_options = {'method':krylov_method,'rdiff':rdiff,'outer_k':outer_k,'inner_tol':inner_tol,'inner_M':inner_M }
            else:
                jac_options = {'method':krylov_method,'rdiff':rdiff,'outer_k':outer_k,'inner_tol':inner_tol,'inner_M':inner_M }

            jacobian = NBS.GetKrylovJacobian(Use_exact_Jacobian, jac_options)

            def optim_callback(x,f,f_norm):

                AskedForNext = False
                best_sol.update(x,f,f_norm)

                for i in range(n_optim_callback_list):
                    AskedForNext = (AskedForNext or optim_callback_list[i](x,f,f_norm,NBS,jacobian))

                return AskedForNext

            try : 
                
                opt_result , info = choreo.scipy_plus.nonlin.nonlin_solve_pp(
                    F=NBS.params_to_action_grad, x0=x, jacobian=jacobian, 
                    verbose=disp_scipy_opt, maxiter=maxiter, f_tol=gradtol,  line_search=line_search, callback=optim_callback, raise_exception=False,smin=linesearch_smin, full_output=True, tol_norm=np.linalg.norm)

                AskedForNext = (info['status'] == 0)

            except Exception as exc:
                
                print(exc)
                GoOn = False
                raise(exc)

            if (AskedForNext):
                print("Skipping at user's request")
                GoOn = False

            SaveSol = False

            segmpos = NBS.params_to_segmpos(best_sol.x)
            Hash_Action = NBS.segmpos_to_hash(segmpos)
            
            print(f'Opt Action Grad Norm: {best_sol.f_norm:.2e}')
            
            if (GoOn and Check_Escape):
                
                Escaped = NBS.DetectEscape(segmpos)

                if Escaped:
                    print('One loop escaped. Starting over.')    
                    
                GoOn = GoOn and not(Escaped)
                
            if (GoOn and Look_for_duplicates):
                
                Found_duplicate, file_path = Check_Duplicates(NBS, segmpos, best_sol.x, hash_dict, action_dict, store_folder, duplicate_eps, Hash_Action=Hash_Action, Duplicates_Hash=Duplicates_Hash)
                
                if (Found_duplicate):
                
                    print('Found Duplicate!')   
                    print('Path: ',file_path)
                    
                GoOn = GoOn and not(Found_duplicate)
                
            if (GoOn):
                
                nint_fac_cur = NBS.nint_fac
                nint_fac = 2*nint_fac_cur
                x_fine = NBS.params_resize(best_sol.x, nint_fac)
                NBS.nint_fac = nint_fac
                
                f_fine = NBS.params_to_action_grad(x_fine)
                f_fine_norm = np.linalg.norm(f_fine)
                
                print(f'Opt Action Grad Norm Refine : {f_fine_norm:.2e}')
                
                ParamPreciseEnough = (f_fine_norm < gradtol_max)
                CanChangeOptimParams = i_optim_param < (n_optim_param-1)
                CanRefine = (current_cvg_lvl < n_reconverge_it_max)
                NeedsRefinement = (f_fine_norm > mul_coarse_to_fine*best_sol.f_norm)
                OnCollisionCourse = (best_sol.f_norm < 1e3*gradtol_max) and (f_fine_norm > 1e6 * best_sol.f_norm) 
                
                NBS.nint_fac = nint_fac_cur

                if GoOn and ParamPreciseEnough and not(NeedsRefinement):

                    GoOn = False
                    print("Stopping search: found solution.")
                    SaveSol = True

                if GoOn and ParamPreciseEnough and not(CanChangeOptimParams) :

                    GoOn = False
                    print("Stopping search: found approximate solution.")
                    SaveSol = True

                if GoOn and (not(CanRefine) or not(NeedsRefinement)) and not(CanChangeOptimParams):
                
                    GoOn = False
                    print('Stopping search: could not converge within prescibed optimizer and refinement parameters.')
                    
                if GoOn and (OnCollisionCourse):
                
                    GoOn = False
                    print('Stopping search: solver is likely narrowing in on a collision solution.')

                if SaveSol :
                    
                    GoOn  = False

                    max_num_file = 0
                    
                    for filename in os.listdir(store_folder):
                        file_path = os.path.join(store_folder, filename)
                        file_root, file_ext = os.path.splitext(os.path.basename(file_path))
                        
                        if (file_basename in file_root) and (file_ext == '.json' ):

                            file_root = file_root.replace(file_basename,"")

                            try:
                                max_num_file = max(max_num_file,int(file_root))
                            except:
                                pass

                    max_num_file = max_num_file + 1
                    n_find = max_num_file

                    if (AddNumberToOutputName):   

                        filename_output = os.path.join(store_folder,file_basename+str(max_num_file).zfill(5))

                    else:

                        filename_output = os.path.join(store_folder,file_basename)

                    print(f'Saving solution as {filename_output}.*.')
             
                    NBS.Write_Descriptor(best_sol.x , filename = filename_output+'.json', segmpos=segmpos, Gradaction=f_fine_norm, Hash_Action=Hash_Action, extend=plot_extend)

                    if Save_img :
                        NBS.plot_segmpos_2D(segmpos, filename_output+'.png', fig_size=img_size, color=color, color_list=color_list)
                    
                    if Save_thumb :
                        NBS.plot_segmpos_2D(segmpos, filename_output+'_thumb.png', fig_size=thumb_size, color=color, color_list=color_list)     
                        
#                     if Save_anim :
#                         ActionSyst.plot_all_2D_anim(best_sol.x,nint_plot_anim,filename_output+'.mp4',nperiod_anim,Plot_trace=Plot_trace_anim,fig_size=vid_size,dnint=dnint,color_list=color_list,color=color)
# 
#                     if Save_Newton_Error :
#                         ActionSyst.plot_Newton_Error(best_sol.x,filename_output+'_newton.png')
# 
#                     if Save_GradientAction_Error :
#                         ActionSyst.plot_GradientAction_Error(best_sol.x,filename_output+'_gradaction.png')
# 
#                     if Save_coeff_profile:
#                         ActionSyst.plot_coeff_profile(best_sol.x,filename_output+'_coeff_profile.png')
# 
#                     if Save_All_Coeffs:
#                         all_coeffs = ActionSyst.Unpackage_all_coeffs(best_sol.x)
#                         np.save(filename_output+'_coeffs.npy',all_coeffs)

                    if Save_SegmPos:
                        np.save(filename_output+'.npy', segmpos)
# 
#                     if Save_Init_Pos_Vel_Sol:
#                         all_pos_b = ActionSyst.Compute_init_pos_vel(best_sol.x)
#                         np.save(filename_output+'_init.npy',all_coeffs)
#                
                if GoOn and NeedsRefinement and CanRefine:
                    
                    print('Resizing.')

                    best_sol = choreo.scipy_plus.nonlin.current_best(x_fine, f_fine)
                    NBS.nint_fac = 2*NBS.nint_fac
                    current_cvg_lvl += 1
                     
                elif GoOn and CanChangeOptimParams:
                    
                    print('Changing optimizer parameters.')
                    
                    i_optim_param += 1

                
            print('')

        print('')

    print('Done!')

def ChoreoFindFromDict(params_dict, extra_args_dict, Workspace_folder):
    
    all_kwargs = ChoreoLoadFromDict(params_dict, Workspace_folder, callback = Find_Choreo, extra_args_dict=extra_args_dict)

    Find_Choreo(**all_kwargs)
        
def ChoreoLoadFromDict(params_dict, Workspace_folder, callback=None, args_list=None, extra_args_dict={}):

    def load_target_files(filename, Workspace_folder, target_speed):

        if (filename == "no file"):

            raise ValueError("A target file is missing")

        else:

            path_list = filename.split("/")

            path_beg = path_list.pop(0)
            path_end = path_list.pop( )

            if (path_beg == "Gallery"):

                json_filename = os.path.join(Workspace_folder,'Temp',target_speed+'.json')
                npy_filename  = os.path.join(Workspace_folder,'Temp',target_speed+'.npy' )

            elif (path_beg == "Workspace"):

                json_filename = os.path.join(Workspace_folder,*path_list,path_end+'.json')
                npy_filename  = os.path.join(Workspace_folder,*path_list,path_end+'.npy' )

            else:

                raise ValueError("Unknown path")

        with open(json_filename) as jsonFile:
            Info_dict = json.load(jsonFile)

        all_pos = np.load(npy_filename)

        return Info_dict, all_pos

    np.random.seed(int(time.time()*10000) % 5000)

    geodim = params_dict['Phys_Gen'] ['geodim']

    TwoDBackend = (geodim == 2)
    ParallelBackend = (params_dict['Solver_CLI']['Exec_Mul_Proc'] == "MultiThread")
    GradHessBackend = params_dict['Solver_CLI']['GradHess_backend']

    file_basename = ''
    
    CrashOnError_changevar = False

    LookForTarget = params_dict['Phys_Target'] ['LookForTarget']

    if (LookForTarget) : # IS LIKELY BROKEN !!!!

        Rotate_fast_with_slow = params_dict['Phys_Target'] ['Rotate_fast_with_slow']
        Optimize_Init = params_dict['Phys_Target'] ['Optimize_Init']
        Randomize_Fast_Init =  params_dict['Phys_Target'] ['Randomize_Fast_Init']
            
        nT_slow = params_dict['Phys_Target'] ['nT_slow']
        nT_fast = params_dict['Phys_Target'] ['nT_fast']

        Info_dict_slow_filename = params_dict['Phys_Target'] ["slow_filename"]
        Info_dict_slow, all_pos_slow = load_target_files(Info_dict_slow_filename,Workspace_folder,"slow")

        ncoeff_slow = Info_dict_slow["n_int"] // 2 + 1

        all_coeffs_slow = AllPosToAllCoeffs(all_pos_slow,ncoeff_slow)
        Center_all_coeffs(all_coeffs_slow,Info_dict_slow["nloop"],Info_dict_slow["mass"],Info_dict_slow["loopnb"],np.array(Info_dict_slow["Targets"]),np.array(Info_dict_slow["SpaceRotsUn"]))

        Info_dict_fast_list = []
        all_coeffs_fast_list = []

        for i in range(len(nT_fast)) :

            Info_dict_fast_filename = params_dict['Phys_Target'] ["fast_filenames"] [i]
            Info_dict_fast, all_pos_fast = load_target_files(Info_dict_fast_filename,Workspace_folder,"fast"+str(i))
            Info_dict_fast_list.append(Info_dict_fast)

            ncoeff_fast = Info_dict_fast["n_int"] // 2 + 1

            all_coeffs_fast = AllPosToAllCoeffs(all_pos_fast,ncoeff_fast)
            Center_all_coeffs(all_coeffs_fast,Info_dict_fast_list[i]["nloop"],Info_dict_fast_list[i]["mass"],Info_dict_fast_list[i]["loopnb"],np.array(Info_dict_fast_list[i]["Targets"]),np.array(Info_dict_fast_list[i]["SpaceRotsUn"]))

            all_coeffs_fast_list.append(all_coeffs_fast)

        Sym_list, mass,il_slow_source,ibl_slow_source,il_fast_source,ibl_fast_source = MakeTargetsSyms(Info_dict_slow,Info_dict_fast_list)
        
        nbody = len(mass)

    nbody = params_dict["Phys_Bodies"]["nbody"]
    MomConsImposed = params_dict['Phys_Bodies'] ['MomConsImposed']
    nsyms = params_dict["Phys_Bodies"]["nsyms"]

    nloop = params_dict["Phys_Bodies"]["nloop"]
    
    mass = np.zeros(nbody)
    for il in range(nloop):
        for ilb in range(len(params_dict["Phys_Bodies"]["Targets"][il])):
            
            ib = params_dict["Phys_Bodies"]["Targets"][il][ilb]
            mass[ib] = params_dict["Phys_Bodies"]["mass"][il]    
            
    charge = np.zeros(nbody)
    try:
        for il in range(nloop):
            for ilb in range(len(params_dict["Phys_Bodies"]["Targets"][il])):                
                ib = params_dict["Phys_Bodies"]["Targets"][il][ilb]
                charge[ib] = params_dict["Phys_Bodies"]["charge"][il]
    except KeyError:
        # TODO: Remove this
        # Replaces charge with mass for backwards compatibility
        for il in range(nloop):
            for ilb in range(len(params_dict["Phys_Bodies"]["Targets"][il])):                
                ib = params_dict["Phys_Bodies"]["Targets"][il][ilb]
                charge[ib] = params_dict["Phys_Bodies"]["mass"][il]

    # TODO: Remove this
    # Backwards compatibility again
    try:
        inter_pow = params_dict["Phys_Inter"]["inter_pow"]
        inter_pm_in = params_dict["Phys_Inter"]["inter_pm"]
        
        if inter_pm_in == "plus":
            inter_pm = 1
        elif inter_pm_in == "minus":
            inter_pm = -1
        else:
            raise ValueError(f"Invalid inter_pm {inter_pm_in}")

    except KeyError:
        inter_pow = -1.
        inter_pm = 1

    Sym_list = []
    
    for isym in range(nsyms):
        
        BodyPerm = np.array(params_dict["Phys_Bodies"]["AllSyms"][isym]["BodyPerm"],dtype=int)

        SpaceRot = params_dict["Phys_Bodies"]["AllSyms"][isym].get("SpaceRot")

        if SpaceRot is None:
            
            if geodim == 2:
                    
                Reflexion = params_dict["Phys_Bodies"]["AllSyms"][isym]["Reflexion"]
                if (Reflexion == "True"):
                    s = -1
                elif (Reflexion == "False"):
                    s = 1
                else:
                    raise ValueError("Reflexion must be True or False")
                    
                rot_angle = 2 * np.pi * params_dict["Phys_Bodies"]["AllSyms"][isym]["RotAngleNum"] / params_dict["Phys_Bodies"]["AllSyms"][isym]["RotAngleDen"]

                SpaceRot = np.array(
                    [   [ s*np.cos(rot_angle)   , -s*np.sin(rot_angle)  ],
                        [   np.sin(rot_angle)   ,    np.cos(rot_angle)  ]   ]
                    , dtype = np.float64
                )

            else:
                
                raise ValueError(f"Provided space dimension: {geodim}. Please give a SpaceRot matrix directly.")
            
        else:
            
            SpaceRot = np.array(SpaceRot, dtype = np.float64)
            
            if SpaceRot.shape != (geodim, geodim):
                raise  ValueError(f"Invalid SpaceRot dimension. {geodim =}, {SpaceRot.shape =}")
                
        TimeRev_str = params_dict["Phys_Bodies"]["AllSyms"][isym]["TimeRev"]
        if (TimeRev_str == "True"):
            TimeRev = -1
        elif (TimeRev_str == "False"):
            TimeRev = 1
        else:
            raise ValueError("TimeRev must be True or False")

        TimeShiftNum = int(params_dict["Phys_Bodies"]["AllSyms"][isym]["TimeShiftNum"])
        TimeShiftDen = int(params_dict["Phys_Bodies"]["AllSyms"][isym]["TimeShiftDen"])

        Sym_list.append(
            ActionSym(
                BodyPerm = BodyPerm     ,
                SpaceRot = SpaceRot     ,
                TimeRev = TimeRev       ,
                TimeShiftNum = TimeShiftNum   ,
                TimeShiftDen = TimeShiftDen   ,
            )
        )

    if ((LookForTarget) and not(params_dict['Phys_Target'] ['RandomJitterTarget'])) :

        coeff_ampl_min  = 0
        coeff_ampl_o    = 0
        k_infl          = 2
        k_max           = 3

    else:

        coeff_ampl_min  = params_dict["Phys_Random"]["coeff_ampl_min"]
        coeff_ampl_o    = params_dict["Phys_Random"]["coeff_ampl_o"]
        k_infl          = params_dict["Phys_Random"]["k_infl"]
        k_max           = params_dict["Phys_Random"]["k_max"]

    CurrentlyDeveloppingNewStuff = params_dict.get("CurrentlyDeveloppingNewStuff",False)

    # if sys.platform == 'emscripten':
    #     store_folder = os.path.join(Workspace_folder,str(nbody))
    # else:
    #     store_folder = os.path.join(Workspace_folder,str(nbody))
    store_folder = os.path.join(Workspace_folder,str(nbody))
    if not(os.path.isdir(store_folder)):
        os.makedirs(store_folder)

    Use_exact_Jacobian = params_dict["Solver_Discr"]["Use_exact_Jacobian"]

    Look_for_duplicates = params_dict["Solver_Checks"]["Look_for_duplicates"]
    Duplicates_Hash = params_dict["Solver_Checks"].get("Duplicates_Hash", True) # Backward compatibility

    Check_Escape = params_dict["Solver_Checks"]["Check_Escape"]

    # Penalize_Escape = True
    Penalize_Escape = False

    save_first_init = (sys.platform == 'emscripten')
    # save_first_init = False
    # save_first_init = True

    save_all_inits = False
    # save_all_inits = True

    Save_img = params_dict['Solver_CLI'] ['SaveImage']

    # Save_thumb = True
    Save_thumb = False

    # img_size = (12,12) # Image size in inches
    img_size = (8,8) # Image size in inches
    thumb_size = (2,2) # Image size in inches
    
    color = params_dict["Animation_Colors"]["color_method_input"]

    color_list = params_dict["Animation_Colors"]["colorLookup"]

    Save_anim =  params_dict['Solver_CLI'] ['SaveVideo']

    vid_size = (8,8) # Image size in inches
    nint_plot_anim = 2*2*2*3*3*5*2
    # nperiod_anim = 1./nbody
    dnint = 30

    nint_plot_img = nint_plot_anim * dnint

    nperiod_anim = 1.

    Plot_trace_anim = True
    # Plot_trace_anim = False

    n_reconverge_it_max = params_dict["Solver_Discr"] ['n_reconverge_it_max'] 
    nint_init = params_dict["Solver_Discr"]["nint_init"]   
    nint_fac_init = nint_init

    disp_scipy_opt =  (params_dict['Solver_Optim'] ['optim_verbose_lvl'] == "full")
    # disp_scipy_opt = False
    # disp_scipy_opt = True
    
    max_norm_on_entry = 1e20

    Newt_err_norm_max = params_dict["Solver_Optim"]["Newt_err_norm_max"]  
    Newt_err_norm_max_save = params_dict["Solver_Optim"]["Newt_err_norm_safe"]  

    duplicate_eps =  params_dict['Solver_Checks'] ['duplicate_eps'] 

    krylov_method = params_dict["Solver_Optim"]["krylov_method"]  

    line_search = params_dict["Solver_Optim"]["line_search"]  
    linesearch_smin = params_dict["Solver_Optim"]["line_search_smin"]  

    gradtol_list =          params_dict["Solver_Loop"]["gradtol_list"]
    inner_maxiter_list =    params_dict["Solver_Loop"]["inner_maxiter_list"]
    maxiter_list =          params_dict["Solver_Loop"]["maxiter_list"]
    outer_k_list =          params_dict["Solver_Loop"]["outer_k_list"]
    store_outer_Av_list =   params_dict["Solver_Loop"]["store_outer_Av_list"]

    n_optim_param = len(gradtol_list)
    
    gradtol_max = 100*gradtol_list[n_optim_param-1]

    escape_fac = 1e0

    escape_min_dist = 1
    escape_pow = 2.0

    n_grad_change = 1.

    freq_erase_dict = 100

    n_opt = 0
    n_opt_max = 100

    mul_coarse_to_fine = params_dict["Solver_Discr"]["mul_coarse_to_fine"]

    # Save_All_Coeffs = True
    Save_All_Coeffs = False

    # Save_Init_Pos_Vel_Sol = True
    Save_Init_Pos_Vel_Sol = False

    n_save_pos = 'auto'

    Save_SegmPos = True
    
    plot_extend = 0.

    n_opt = 0
    # n_opt_max = 1
    n_opt_max = params_dict["Solver_Optim"]["n_opt"]
    if sys.platform == 'emscripten':
        n_find_max = 1
    else:
        n_find_max = params_dict["Solver_Optim"]["n_opt"]
    
    fftw_planner_effort = params_dict['Solver_CLI'].get('fftw_planner_effort', 'FFTW_MEASURE')
    fftw_wisdom_only = params_dict['Solver_CLI'].get('fftw_wisdom_only', False)
    fftw_nthreads = 1
    fft_backend = params_dict['Solver_CLI'].get('fft_backend', 'scipy')
    
    ReconvergeSol = False
    AddNumberToOutputName = not(sys.platform == 'emscripten')
    
    if callback is None:
        if args_list is None:
            return dict(**locals())
        else:
            the_dict = dict(**locals())
            the_dict |= extra_args_dict
            return {key:the_dict[key] for key in args_list}
    else:
        the_dict = dict(**locals())
        the_dict |= extra_args_dict
        return Pick_Named_Args_From_Dict(callback, the_dict)

def Pick_Named_Args_From_Dict(fun, the_dict, MissingArgsAreNone=True):
    
    list_of_args = inspect.getfullargspec(fun).kwonlyargs

    if MissingArgsAreNone:
        all_kwargs = {k:the_dict.get(k) for k in list_of_args}
        
    else:
        all_kwargs = {k:the_dict[k] for k in list_of_args}
    
    return all_kwargs

def ChoreoReadDictAndFind(Workspace_folder, config_filename="choreo_config.json"):
    
    params_filename = os.path.join(Workspace_folder, config_filename)

    with open(params_filename) as jsonFile:
        params_dict = json.load(jsonFile)
        
    ChoreoChooseParallelEnvAndFind(Workspace_folder, params_dict)
    
def ChoreoChooseParallelEnvAndFind(Workspace_folder, params_dict, extra_args_dict={}):
    
    if sys.platform == 'emscripten':
        params_dict['Solver_CLI']['Exec_Mul_Proc'] = "No"
        params_dict['Solver_CLI']['SaveImage'] = False
        params_dict['Solver_CLI']['SaveVideo'] = False
        params_dict['Solver_CLI']['fft_backend'] = "scipy" 


    Exec_Mul_Proc = params_dict['Solver_CLI']['Exec_Mul_Proc']
    n_threads = params_dict['Solver_CLI']['nproc']

    if Exec_Mul_Proc == "MultiProc":

        print(f"Executing with {n_threads} workers")
        
        with threadpoolctl.threadpool_limits(limits=1):
            with concurrent.futures.ProcessPoolExecutor(max_workers=n_threads) as executor:
                
                res = []
                for i in range(n_threads):
                    res.append(executor.submit(ChoreoFindFromDict, params_dict, extra_args_dict, Workspace_folder))
                    time.sleep(0.01)

    elif Exec_Mul_Proc == "MultiThread":
        
        with threadpoolctl.threadpool_limits(limits=n_threads):
            ChoreoFindFromDict(params_dict, extra_args_dict, Workspace_folder)

    elif Exec_Mul_Proc == "No":

        with threadpoolctl.threadpool_limits(limits=1):
            ChoreoFindFromDict(params_dict, extra_args_dict, Workspace_folder)
    else :

        raise ValueError(f'Unknown {Exec_Mul_Proc = }. Accepted values : "MultiProc", "MultiThread" or "No"')

def UpdateHashDict(store_folder, hash_dict, action_dict):
    # Creates a list of possible duplicates based on value of the action and hashes

    file_path_list = []
    for file_path in os.listdir(store_folder):

        file_path = os.path.join(store_folder, file_path)
        file_root, file_ext = os.path.splitext(os.path.basename(file_path))
        
        if (file_ext == '.json' ):
            
            This_Action_Hash = hash_dict.get(file_root)
            This_Action = action_dict.get(file_root)
            
            if (This_Action_Hash is None) :

                This_hash = ReadHashFromFile(file_path) 

                if not(This_hash is None):

                    action_dict[file_root] = This_hash[0]
                    hash_dict[file_root] = This_hash[1]


def ReadHashFromFile(filename):

    with open(filename,'r') as jsonFile:
        Info_dict = json.load(jsonFile)

    if Info_dict.get("choreo_version") == choreo.metadata.__version__:
        
        the_hash = Info_dict.get("Hash")
        the_action = Info_dict.get("Action")

        if the_hash is None:
            return None
        else:
            return the_action, np.array(the_hash)
    else:
        return None

def Check_Duplicates(NBS, segmpos, params, hash_dict, action_dict, store_folder, duplicate_eps, Action=None, Hash_Action=None, Duplicates_Hash=True):
    r"""
    Checks whether there is a duplicate of a given trajecory in the provided folder
    """
    
    UpdateHashDict(store_folder, hash_dict, action_dict)
    
    if Duplicates_Hash:

        if Hash_Action is None:
            Hash_Action = NBS.segmpos_to_hash(segmpos)
        
        for file_path, found_hash in hash_dict.items():
            
            IsCandidate = NBS.TestHashSame(Hash_Action, found_hash, duplicate_eps)

            if IsCandidate:
                return True, file_path
    else:

        if Action is None:
            Action = NBS.segmpos_params_to_action(segmpos, params)
        
        for file_path, found_action in action_dict.items():
            
            IsCandidate = NBS.TestActionSame(Action, found_action, duplicate_eps)

            if IsCandidate:
                return True, file_path

    return False, None

try:
    import pyfftw

    def wisdom_filename_divide(filename):
        root, ext = os.path.splitext(filename) 
        return [root+"_"+prec+ext for prec in ['d','f','l']]

    def Load_wisdom_file(DP_Wisdom_file):
        
        wis_list = []
        
        for i, filename in enumerate(wisdom_filename_divide(DP_Wisdom_file)):

            if os.path.isfile(filename):
                with open(filename, 'rb') as f:
                    wis = f.read()
            else:
                wis = b''
                    
            wis_list.append(wis)

        pyfftw.import_wisdom(wis_list)
        
    def Write_wisdom_file(DP_Wisdom_file):    
        wis = pyfftw.export_wisdom()
        
        for i, filename in enumerate(wisdom_filename_divide(DP_Wisdom_file)):
            with open(filename, 'wb') as f:
                f.write(wis[i])

except:
    pass