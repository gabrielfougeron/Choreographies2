#cython: language_level=3, boundscheck=False, wraparound = False

import os
import numpy as np
cimport numpy as np
cimport cython

from libc.math cimport pow as cpow
from libc.math cimport fabs as cfabs
from libc.math cimport cos as ccos
from libc.math cimport sin as csin
from libc.math cimport sqrt as csqrt
from libc.math cimport isnan as cisnan
from libc.math cimport isinf as cisinf
import time

cdef long ndim = 2

cdef double n = -0.5  #coeff of x^2 in the potential power law
cdef double nm1 = n-1  #coeff of x^2 in the potential power law
cdef double nm2 = n-2  #coeff of x^2 in the potential power law

cdef double nppi = np.pi
cdef double twopi = 2* np.pi
cdef double fourpi = 4 * np.pi
cdef double fourpisq = twopi*twopi

cdef double nnm1 = n*(n-1)

cdef double mn = -n
cdef double mnnm1 = -nnm1

cdef inline (double, double, double) CCpt_interbody_pot(double xsq):  # xsq is the square of the distance between two bodies !
    
    cdef double a = cpow(xsq,nm2)
    cdef double b = xsq*a
    
    cdef double pot = -xsq*b
    cdef double potp = mn*b
    cdef double potpp = mnnm1*a
    
    return pot,potp,potpp
    
def Cpt_interbody_pot(double xsq): 
    return CCpt_interbody_pot(xsq)
    

# cdef  np.ndarray[double, ndim=1, mode="c"] hash_exps = np.array([0.3,0.4,0.6],dtype=np.float64)
# cdef long cnhash = hash_exps.size
# Unfortunately, Cython does not allow that. Let's do it manually then

cdef double hash_exp0 = 0.3
cdef double hash_exp1 = 0.4
cdef double hash_exp2 = 0.6

cdef long cnhash = 3

nhash = cnhash
    
def CCpt_hash_pot(double xsq):  # xsq is the square of the distance between two bodies !
    
    cdef np.ndarray[double, ndim=1, mode="c"] hash_pots = np.zeros((cnhash),dtype=np.float64)

    hash_pots[0] = cpow(xsq,hash_exp0)
    hash_pots[1] = cpow(xsq,hash_exp1)
    hash_pots[2] = cpow(xsq,hash_exp2)
    
    return hash_pots
    
def Compute_action_Cython(
    long nloop,
    long ncoeff,
    long nint,
    np.ndarray[double, ndim=1, mode="c"] mass not None ,
    np.ndarray[long  , ndim=1, mode="c"] loopnb not None ,
    np.ndarray[long  , ndim=2, mode="c"] Targets not None ,
    np.ndarray[double, ndim=1, mode="c"] MassSum not None ,
    np.ndarray[double, ndim=4, mode="c"] SpaceRotsUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeRevsUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftNumUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftDenUn not None ,
    np.ndarray[long  , ndim=1, mode="c"] loopnbi not None ,
    np.ndarray[double, ndim=2, mode="c"] ProdMassSumAll not None ,
    np.ndarray[double, ndim=4, mode="c"] SpaceRotsBin not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeRevsBin not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftNumBin not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftDenBin not None ,
    np.ndarray[double, ndim=4, mode="c"] all_coeffs  not None
    ):

    cdef long il,ilp,i
    cdef long idim,idimp
    cdef long ibi
    cdef long ib,ibp
    cdef long iint
    cdef long div
    cdef long k,kp,k2
    cdef double pot,potp,potpp
    cdef double prod_mass,a,b,dx2,prod_fac
    cdef np.ndarray[double, ndim=1, mode="c"]  dx = np.zeros((ndim),dtype=np.float64)
    cdef np.ndarray[double, ndim=1, mode="c"]  df = np.zeros((ndim),dtype=np.float64)
        
    cdef long maxloopnb = loopnb.max()
    cdef long maxloopnbi = loopnbi.max()
    
    cdef double Kin_en = 0

    cdef np.ndarray[double, ndim=4, mode="c"] Action_grad = np.zeros((nloop,ndim,ncoeff,2),np.float64)

    for il in range(nloop):
        
        prod_fac = MassSum[il]*fourpisq
        
        for idim in range(ndim):
            for k in range(1,ncoeff):
                
                k2 = k*k
                a = prod_fac*k2
                b=2*a

                Kin_en += a *((all_coeffs[il,idim,k,0]*all_coeffs[il,idim,k,0]) + (all_coeffs[il,idim,k,1]*all_coeffs[il,idim,k,1]))
                
                Action_grad[il,idim,k,0] += b*all_coeffs[il,idim,k,0]
                Action_grad[il,idim,k,1] += b*all_coeffs[il,idim,k,1]
        
    cdef double Pot_en = 0.

    c_coeffs = all_coeffs.view(dtype=np.complex128)[...,0]
    
    cdef np.ndarray[double, ndim=3, mode="c"] all_pos = np.fft.irfft(c_coeffs,n=nint,axis=2)*nint

    cdef np.ndarray[long, ndim=2, mode="c"]  all_shiftsUn = np.zeros((nloop,maxloopnb),dtype=np.int_)
    cdef np.ndarray[long, ndim=2, mode="c"]  all_shiftsBin = np.zeros((nloop,maxloopnbi),dtype=np.int_)
    
    for il in range(nloop):
        for ib in range(loopnb[il]):
                
            if not(((-TimeRevsUn[il,ib]*nint*TimeShiftNumUn[il,ib]) % TimeShiftDenUn[il,ib]) == 0):
                print("WARNING : remainder in integer division")
                
            all_shiftsUn[il,ib] = ((-TimeRevsUn[il,ib]*nint*TimeShiftNumUn[il,ib]) // TimeShiftDenUn[il,ib] ) % nint
        
        for ibi in range(loopnbi[il]):

            if not(((-TimeRevsBin[il,ibi]*nint*TimeShiftNumBin[il,ibi]) % TimeShiftDenBin[il,ibi]) == 0):
                print("WARNING : remainder in integer division")
                
            all_shiftsBin[il,ibi] = ((-TimeRevsBin[il,ibi]*nint*TimeShiftNumBin[il,ibi]) // TimeShiftDenBin[il,ibi]) % nint
    
    cdef np.ndarray[double, ndim=3, mode="c"] grad_pot_all = np.zeros((nloop,ndim,nint),dtype=np.float64)

    for iint in range(nint):

        # Different loops
        for il in range(nloop):
            for ilp in range(il+1,nloop):

                for ib in range(loopnb[il]):
                    for ibp in range(loopnb[ilp]):
                        
                        prod_mass = mass[Targets[il,ib]]*mass[Targets[ilp,ibp]]

                        for idim in range(ndim):
                            dx[idim] = SpaceRotsUn[il,ib,idim,0]*all_pos[il,0,all_shiftsUn[il,ib]] - SpaceRotsUn[ilp,ibp,idim,0]*all_pos[ilp,0,all_shiftsUn[ilp,ibp]]
                            for jdim in range(1,ndim):
                                dx[idim] += SpaceRotsUn[il,ib,idim,jdim]*all_pos[il,jdim,all_shiftsUn[il,ib]] - SpaceRotsUn[ilp,ibp,idim,jdim]*all_pos[ilp,jdim,all_shiftsUn[ilp,ibp]]

                        dx2 = dx[0]*dx[0]
                        for idim in range(1,ndim):
                            dx2 += dx[idim]*dx[idim]
                            
                        pot,potp,potpp = CCpt_interbody_pot(dx2)
                        
                        Pot_en += pot*prod_mass

                        a = (2*prod_mass*potp)

                        for idim in range(ndim):
                            dx[idim] = a*dx[idim]

                        for idim in range(ndim):
                            
                            b = SpaceRotsUn[il,ib,0,idim]*dx[0]
                            for jdim in range(1,ndim):
                                b+=SpaceRotsUn[il,ib,jdim,idim]*dx[jdim]
                            
                            grad_pot_all[il ,idim,all_shiftsUn[il ,ib ]] += b
                            
                            b = SpaceRotsUn[ilp,ibp,0,idim]*dx[0]
                            for jdim in range(1,ndim):
                                b+=SpaceRotsUn[ilp,ibp,jdim,idim]*dx[jdim]
                            
                            grad_pot_all[ilp,idim,all_shiftsUn[ilp,ibp]] -= b

        # Same loop + symmetry
        for il in range(nloop):

            for ibi in range(loopnbi[il]):
                
                for idim in range(ndim):
                    dx[idim] = SpaceRotsBin[il,ibi,idim,0]*all_pos[il,0,all_shiftsBin[il,ibi]]
                    for jdim in range(1,ndim):
                        dx[idim] += SpaceRotsBin[il,ibi,idim,jdim]*all_pos[il,jdim,all_shiftsBin[il,ibi]]
                    
                    dx[idim] -= all_pos[il,idim,iint]
                    
                dx2 = dx[0]*dx[0]
                for idim in range(1,ndim):
                    dx2 += dx[idim]*dx[idim]

                pot,potp,potpp = CCpt_interbody_pot(dx2)
                
                Pot_en += pot*ProdMassSumAll[il,ibi]
                
                a = (2*ProdMassSumAll[il,ibi]*potp)

                for idim in range(ndim):
                    dx[idim] = a*dx[idim]

                for idim in range(ndim):
                    
                    b = SpaceRotsBin[il,ibi,0,idim]*dx[0]
                    for jdim in range(1,ndim):
                        b+=SpaceRotsBin[il,ibi,jdim,idim]*dx[jdim]
                    
                    grad_pot_all[il ,idim,all_shiftsBin[il,ibi]] += b
                    
                    grad_pot_all[il ,idim,iint] -= dx[idim]

        # Increments time at the end
        for il in range(nloop):
            for ib in range(loopnb[il]):
                all_shiftsUn[il,ib] = (all_shiftsUn[il,ib]+TimeRevsUn[il,ib]) % nint
                
            for ibi in range(loopnbi[il]):
                all_shiftsBin[il,ibi] = (all_shiftsBin[il,ibi]+TimeRevsBin[il,ibi]) % nint

    cdef np.ndarray[doublecomplex , ndim=3, mode="c"]  grad_pot_fft = np.fft.ihfft(grad_pot_all,nint)


    for il in range(nloop):
        for idim in range(ndim):
            
            Action_grad[il,idim,0,0] -= grad_pot_fft[il,idim,0].real
            
            for k in range(1,ncoeff):
            
                Action_grad[il,idim,k,0] -= 2*grad_pot_fft[il,idim,k].real
                Action_grad[il,idim,k,1] += 2*grad_pot_fft[il,idim,k].imag

    Pot_en = Pot_en / nint
    
    Action = Kin_en-Pot_en
    
    if cisnan(Action):
        print("Action is NaN.")
    if cisinf(Action):
        print("Action is Infinity. Likely explaination : two body positions might have been identical")
    
    return Action,Action_grad
    
def Compute_hash_action_Cython(
    long nloop,
    long ncoeff,
    long nint,
    np.ndarray[double, ndim=1, mode="c"] mass not None ,
    np.ndarray[long  , ndim=1, mode="c"] loopnb not None ,
    np.ndarray[long  , ndim=2, mode="c"] Targets not None ,
    np.ndarray[double, ndim=1, mode="c"] MassSum not None ,
    np.ndarray[double, ndim=4, mode="c"] SpaceRotsUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeRevsUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftNumUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftDenUn not None ,
    np.ndarray[long  , ndim=1, mode="c"] loopnbi not None ,
    np.ndarray[double, ndim=2, mode="c"] ProdMassSumAll not None ,
    np.ndarray[double, ndim=4, mode="c"] SpaceRotsBin not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeRevsBin not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftNumBin not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftDenBin not None ,
    np.ndarray[double, ndim=4, mode="c"] all_coeffs  not None
    ):

    cdef long il,ilp,i
    cdef long idim,idimp
    cdef long ibi
    cdef long ib,ibp
    cdef long iint
    cdef long div
    cdef long k,kp,k2
    cdef double pot,potp,potpp
    cdef double prod_mass,a,b,dx2,prod_fac
    cdef np.ndarray[double, ndim=1, mode="c"]  dx = np.zeros((ndim),dtype=np.float64)
        
    cdef long maxloopnb = loopnb.max()
    cdef long maxloopnbi = loopnbi.max()
    
    cdef long ihash
    
    cdef np.ndarray[double, ndim=1, mode="c"]  Hash_En = np.zeros((cnhash),dtype=np.float64)
    cdef np.ndarray[double, ndim=1, mode="c"]  Hash_pot = np.zeros((cnhash),dtype=np.float64)

    c_coeffs = all_coeffs.view(dtype=np.complex128)[...,0]
    
    cdef np.ndarray[double, ndim=3, mode="c"] all_pos = np.fft.irfft(c_coeffs,n=nint,axis=2)*nint

    cdef np.ndarray[long, ndim=2, mode="c"]  all_shiftsUn = np.zeros((nloop,maxloopnb),dtype=np.int_)
    cdef np.ndarray[long, ndim=2, mode="c"]  all_shiftsBin = np.zeros((nloop,maxloopnbi),dtype=np.int_)
    
    for il in range(nloop):
        for ib in range(loopnb[il]):
                
            if not(((-TimeRevsUn[il,ib]*nint*TimeShiftNumUn[il,ib]) % TimeShiftDenUn[il,ib]) == 0):
                print("WARNING : remainder in integer division")
                
            all_shiftsUn[il,ib] = ((-TimeRevsUn[il,ib]*nint*TimeShiftNumUn[il,ib]) // TimeShiftDenUn[il,ib] ) % nint
        
        for ibi in range(loopnbi[il]):

            if not(((-TimeRevsBin[il,ibi]*nint*TimeShiftNumBin[il,ibi]) % TimeShiftDenBin[il,ibi]) == 0):
                print("WARNING : remainder in integer division")
                
            all_shiftsBin[il,ibi] = ((-TimeRevsBin[il,ibi]*nint*TimeShiftNumBin[il,ibi]) // TimeShiftDenBin[il,ibi]) % nint
    
    cdef np.ndarray[double, ndim=3, mode="c"] grad_pot_all = np.zeros((nloop,ndim,nint),dtype=np.float64)

    for iint in range(nint):

        # Different loops
        for il in range(nloop):
            for ilp in range(il+1,nloop):

                for ib in range(loopnb[il]):
                    for ibp in range(loopnb[ilp]):
                        
                        prod_mass = mass[Targets[il,ib]]*mass[Targets[ilp,ibp]]

                        for idim in range(ndim):
                            dx[idim] = SpaceRotsUn[il,ib,idim,0]*all_pos[il,0,all_shiftsUn[il,ib]] - SpaceRotsUn[ilp,ibp,idim,0]*all_pos[ilp,0,all_shiftsUn[ilp,ibp]]
                            for jdim in range(1,ndim):
                                dx[idim] += SpaceRotsUn[il,ib,idim,jdim]*all_pos[il,jdim,all_shiftsUn[il,ib]] - SpaceRotsUn[ilp,ibp,idim,jdim]*all_pos[ilp,jdim,all_shiftsUn[ilp,ibp]]

                        dx2 = dx[0]*dx[0]
                        for idim in range(1,ndim):
                            dx2 += dx[idim]*dx[idim]
                            
                        Hash_pot = CCpt_hash_pot(dx2)
                        
                        for ihash in range(cnhash):
                            Hash_En[ihash] += Hash_pot[ihash] * prod_mass

        # Same loop + symmetry
        for il in range(nloop):

            for ibi in range(loopnbi[il]):
                
                for idim in range(ndim):
                    dx[idim] = SpaceRotsBin[il,ibi,idim,0]*all_pos[il,0,all_shiftsBin[il,ibi]]
                    for jdim in range(1,ndim):
                        dx[idim] += SpaceRotsBin[il,ibi,idim,jdim]*all_pos[il,jdim,all_shiftsBin[il,ibi]]
                    
                    dx[idim] -= all_pos[il,idim,iint]
                    
                dx2 = dx[0]*dx[0]
                for idim in range(1,ndim):
                    dx2 += dx[idim]*dx[idim]

                Hash_pot = CCpt_hash_pot(dx2)
                
                for ihash in range(cnhash):
                    Hash_En[ihash] += Hash_pot[ihash] * ProdMassSumAll[il,ibi]


        # Increments time at the end
        for il in range(nloop):
            for ib in range(loopnb[il]):
                all_shiftsUn[il,ib] = (all_shiftsUn[il,ib]+TimeRevsUn[il,ib]) % nint
                
            for ibi in range(loopnbi[il]):
                all_shiftsBin[il,ibi] = (all_shiftsBin[il,ibi]+TimeRevsBin[il,ibi]) % nint

    return Hash_En
    
def Compute_MinDist_Cython(
    long nloop,
    long ncoeff,
    long nint,
    np.ndarray[double, ndim=1, mode="c"] mass not None ,
    np.ndarray[long  , ndim=1, mode="c"] loopnb not None ,
    np.ndarray[long  , ndim=2, mode="c"] Targets not None ,
    np.ndarray[double, ndim=1, mode="c"] MassSum not None ,
    np.ndarray[double, ndim=4, mode="c"] SpaceRotsUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeRevsUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftNumUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftDenUn not None ,
    np.ndarray[long  , ndim=1, mode="c"] loopnbi not None ,
    np.ndarray[double, ndim=2, mode="c"] ProdMassSumAll not None ,
    np.ndarray[double, ndim=4, mode="c"] SpaceRotsBin not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeRevsBin not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftNumBin not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftDenBin not None ,
    np.ndarray[double, ndim=4, mode="c"]  all_coeffs  not None
    ):

    cdef long il,ilp,i
    cdef long idim,idimp
    cdef long ibi
    cdef long ib,ibp
    cdef long iint
    cdef long div
    cdef long k,kp,k2
    cdef double pot,potp,potpp
    cdef double prod_mass,a,b,dx2,prod_fac
    cdef np.ndarray[double, ndim=1, mode="c"]  dx = np.zeros((ndim),dtype=np.float64)
    cdef np.ndarray[double, ndim=1, mode="c"]  df = np.zeros((ndim),dtype=np.float64)
        
    cdef long maxloopnb = loopnb.max()
    cdef long maxloopnbi = loopnbi.max()
    
    cdef double dx2min = 1e100

    c_coeffs = all_coeffs.view(dtype=np.complex128)[...,0]
    
    cdef np.ndarray[double, ndim=3, mode="c"] all_pos = np.fft.irfft(c_coeffs,n=nint,axis=2)*nint

    cdef np.ndarray[long, ndim=2, mode="c"]  all_shiftsUn = np.zeros((nloop,maxloopnb),dtype=np.int_)
    cdef np.ndarray[long, ndim=2, mode="c"]  all_shiftsBin = np.zeros((nloop,maxloopnbi),dtype=np.int_)
    
    for il in range(nloop):
        for ib in range(loopnb[il]):
                
            if not(((-TimeRevsUn[il,ib]*nint*TimeShiftNumUn[il,ib]) % TimeShiftDenUn[il,ib]) == 0):
                print("WARNING : remainder in integer division")
                
            all_shiftsUn[il,ib] = ((-TimeRevsUn[il,ib]*nint*TimeShiftNumUn[il,ib]) // TimeShiftDenUn[il,ib] ) % nint
        
        for ibi in range(loopnbi[il]):

            if not(((-TimeRevsBin[il,ibi]*nint*TimeShiftNumBin[il,ibi]) % TimeShiftDenBin[il,ibi]) == 0):
                print("WARNING : remainder in integer division")
                
            all_shiftsBin[il,ibi] = ((-TimeRevsBin[il,ibi]*nint*TimeShiftNumBin[il,ibi]) // TimeShiftDenBin[il,ibi]) % nint

    for iint in range(nint):

        # Different loops
        for il in range(nloop):
            for ilp in range(il+1,nloop):

                for ib in range(loopnb[il]):
                    for ibp in range(loopnb[ilp]):
                        
                        for idim in range(ndim):
                            dx[idim] = SpaceRotsUn[il,ib,idim,0]*all_pos[il,0,all_shiftsUn[il,ib]] - SpaceRotsUn[ilp,ibp,idim,0]*all_pos[ilp,0,all_shiftsUn[ilp,ibp]]
                            for jdim in range(1,ndim):
                                dx[idim] += SpaceRotsUn[il,ib,idim,jdim]*all_pos[il,jdim,all_shiftsUn[il,ib]] - SpaceRotsUn[ilp,ibp,idim,jdim]*all_pos[ilp,jdim,all_shiftsUn[ilp,ibp]]

                        dx2 = dx[0]*dx[0]
                        for idim in range(1,ndim):
                            dx2 += dx[idim]*dx[idim]
                            
                        if (dx2 < dx2min):
                            dx2min = dx2
                            
        # Same loop + symmetry
        for il in range(nloop):

            for ibi in range(loopnbi[il]):
                
                for idim in range(ndim):
                    dx[idim] = SpaceRotsBin[il,ibi,idim,0]*all_pos[il,0,all_shiftsBin[il,ibi]]
                    for jdim in range(1,ndim):
                        dx[idim] += SpaceRotsBin[il,ibi,idim,jdim]*all_pos[il,jdim,all_shiftsBin[il,ibi]]
                    
                    dx[idim] -= all_pos[il,idim,iint]
                    
                dx2 = dx[0]*dx[0]
                for idim in range(1,ndim):
                    dx2 += dx[idim]*dx[idim]
                    
                if (dx2 < dx2min):
                    dx2min = dx2

        # Increments time at the end
        for il in range(nloop):
            for ib in range(loopnb[il]):
                all_shiftsUn[il,ib] = (all_shiftsUn[il,ib]+TimeRevsUn[il,ib]) % nint
                
            for ibi in range(loopnbi[il]):
                all_shiftsBin[il,ibi] = (all_shiftsBin[il,ibi]+TimeRevsBin[il,ibi]) % nint

    return csqrt(dx2min)
    
def Compute_action_hess_mul(
    long nloop,
    np.ndarray[long, ndim=1, mode="c"] nbody  not None ,
    long ncoeff,
    np.ndarray[double, ndim=1, mode="c"] mass  not None ,
    long nint,
    np.ndarray[double, ndim=4, mode="c"]  all_coeffs  not None ,
    np.ndarray[double, ndim=4, mode="c"]  all_coeffs_d  not None ,
    ):

    cdef np.ndarray[double, ndim=4, mode="c"] Action_hess_dx = np.zeros((nloop,ndim,ncoeff,2),np.float64)

    c_coeffs = all_coeffs.view(dtype=np.complex128)[...,0]
    cdef np.ndarray[double, ndim=3, mode="c"]  all_pos = np.fft.irfft(c_coeffs,n=nint,axis=2)*nint

    c_coeffs_d = all_coeffs_d.view(dtype=np.complex128)[...,0]
    cdef np.ndarray[double, ndim=3, mode="c"]  all_pos_d = np.fft.irfft(c_coeffs_d,n=nint,axis=2)*nint

    cdef long il,ilp,i
    cdef long idim,idimp
    cdef long ib,ibp
    cdef long iint
    cdef long div
    cdef long k,kp,k2
    cdef double pot,potp,potpp
    cdef double prod_mass,a,b,dx2,prod_fac,dxtddx,c
    cdef np.ndarray[double, ndim=1, mode="c"]  dx = np.zeros((ndim),dtype=np.float64)
    cdef np.ndarray[double, ndim=1, mode="c"]  ddx = np.zeros((ndim),dtype=np.float64)
    cdef np.ndarray[double, ndim=1, mode="c"]  dhdx = np.zeros((ndim),dtype=np.float64)
        
    cdef long maxnbody = nbody.max()

    cdef np.ndarray[long, ndim=2, mode="c"]  all_shifts = np.zeros((nloop,maxnbody),dtype=np.int_)
    
    # Prepares data
    for il in range(nloop):
        
        if not(( nint % nbody[il] ) == 0):
            print("WARNING : remainder in integer division")
        
        div = nint // nbody[il]
        
        for i in range(nbody[il]):
            all_shifts[il,i] = (-i*div)% nint

    for il in range(nloop):
        
        prod_fac = mass[il]*nbody[il]*fourpisq
        
        for idim in range(ndim):
            for k in range(1,ncoeff):
                
                k2 = k*k
                a = 2*prod_fac*k2
                
                Action_hess_dx[il,idim,k,0] += a*all_coeffs_d[il,idim,k,0]
                Action_hess_dx[il,idim,k,1] += a*all_coeffs_d[il,idim,k,1]
    

    cdef np.ndarray[double, ndim=3, mode="c"] hess_pot_all_d = np.zeros((nloop,ndim,nint),dtype=np.float64)

    for iint in range(nint):
        
        for il in range(nloop):
            for ib in range(nbody[il]):
                all_shifts[il,ib] = (all_shifts[il,ib]+1) % nint

        # Different loops
        for il in range(nloop):
            for ilp in range(il+1,nloop):
                
                prod_mass = mass[il]*mass[ilp]
                
                for ib in range(nbody[il]):
                    for ibp in range(nbody[ilp]):
                        
                        for idim in range(ndim):
                            dx[idim]  = all_pos[il,idim,all_shifts[il,ib]] - all_pos[ilp,idim,all_shifts[ilp,ibp]]
                            ddx[idim] = all_pos_d[il,idim,all_shifts[il,ib]] - all_pos_d[ilp,idim,all_shifts[ilp,ibp]]

                        dx2 = dx[0]*dx[0]
                        dxtddx = dx[0]*ddx[0]
                        for idim in range(1,ndim):
                            dx2 += dx[idim]*dx[idim]
                            dxtddx += dx[idim]*ddx[idim]
                        
                        pot,potp,potpp = CCpt_interbody_pot(dx2)
                        
                        a = 2*prod_mass*potp
                        b = (4*prod_mass*potpp*dxtddx)

                        for idim in range(ndim):
                            c = b*dx[idim] + a*ddx[idim]
                            
                            hess_pot_all_d[il ,idim,all_shifts[il ,ib ]] += c
                            hess_pot_all_d[ilp,idim,all_shifts[ilp,ibp]] -= c

                        
        i_sp = 0
        # Same loop + symmetry
        for il in range(nloop):

            prod_mass = (nbody[il]*mass[il]*mass[il])/2
            
            for ib in range(1,nbody[il]):

                for idim in range(ndim):
                    dx[idim]  = all_pos[il,idim,all_shifts[il,ib]] - all_pos[il,idim,all_shifts[il,0]]
                    ddx[idim] = all_pos_d[il,idim,all_shifts[il,ib]] - all_pos_d[il,idim,all_shifts[il,0]]

                dx2 = dx[0]*dx[0]
                dxtddx = dx[0]*ddx[0]
                for idim in range(1,ndim):
                    dx2 += dx[idim]*dx[idim]
                    dxtddx += dx[idim]*ddx[idim]
                
                pot,potp,potpp = CCpt_interbody_pot(dx2)
                
                a = 2*prod_mass*potp
                b = (4*prod_mass*potpp*dxtddx)

                for idim in range(ndim):
                    c = b*dx[idim] + a*ddx[idim]
                    
                    hess_pot_all_d[il,idim,all_shifts[il,ib ]] += c
                    hess_pot_all_d[il,idim,all_shifts[il,0  ]] -= c

    cdef np.ndarray[doublecomplex , ndim=3, mode="c"]  hess_dx_pot_fft = np.fft.ihfft(hess_pot_all_d,nint)
    
    for il in range(nloop):
        for idim in range(ndim):
            
            Action_hess_dx[il,idim,0,0] -= hess_dx_pot_fft[il,idim,0].real
            
            for k in range(1,ncoeff):
           
                Action_hess_dx[il,idim,k,0] -= 2*hess_dx_pot_fft[il,idim,k].real
                Action_hess_dx[il,idim,k,1] += 2*hess_dx_pot_fft[il,idim,k].imag

    return Action_hess_dx

def Compute_Newton_err_Cython(
    long nbody,
    long nloop,
    long ncoeff,
    long nint,
    np.ndarray[double, ndim=1, mode="c"] mass not None ,
    np.ndarray[long  , ndim=1, mode="c"] loopnb not None ,
    np.ndarray[long  , ndim=2, mode="c"] Targets not None ,
    np.ndarray[double, ndim=4, mode="c"] SpaceRotsUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeRevsUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftNumUn not None ,
    np.ndarray[long  , ndim=2, mode="c"] TimeShiftDenUn not None ,
    np.ndarray[double, ndim=4, mode="c"] all_coeffs  not None
    ):

    cdef long il,ilp,i
    cdef long idim,idimp
    cdef long ibi
    cdef long ib,ibp
    cdef long iint
    cdef long div
    cdef long k,kp,k2
    cdef double pot,potp,potpp
    cdef double prod_mass,a,b,dx2,prod_fac
    cdef np.ndarray[double, ndim=1, mode="c"]  dx = np.zeros((ndim),dtype=np.float64)
        
    cdef long maxloopnb = loopnb.max()
    
    cdef np.ndarray[double, ndim=4, mode="c"] acc_coeff = np.zeros((nloop,ndim,ncoeff,2),dtype=np.float64)

    for il in range(nloop):
        for idim in range(ndim):
            for k in range(ncoeff):
                
                k2 = k*k
                acc_coeff[il,idim,k,0] = k2*fourpisq*all_coeffs[il,idim,k,0]
                acc_coeff[il,idim,k,1] = k2*fourpisq*all_coeffs[il,idim,k,1]
                
    c_acc_coeffs = acc_coeff.view(dtype=np.complex128)[...,0]
    cdef np.ndarray[double, ndim=3, mode="c"] all_acc = np.fft.irfft(c_acc_coeffs,n=nint,axis=2)*nint
    
    cdef np.ndarray[double, ndim=3, mode="c"] all_Newt_err = np.zeros((nbody,ndim,nint),np.float64)
    
    c_coeffs = all_coeffs.view(dtype=np.complex128)[...,0]
    
    cdef np.ndarray[double, ndim=3, mode="c"] all_pos = np.fft.irfft(c_coeffs,n=nint,axis=2)*nint

    cdef np.ndarray[long, ndim=2, mode="c"]  all_shiftsUn = np.zeros((nloop,maxloopnb),dtype=np.int_)
    
    for il in range(nloop):
        for ib in range(loopnb[il]):
                
            if not(((-TimeRevsUn[il,ib]*nint*TimeShiftNumUn[il,ib]) % TimeShiftDenUn[il,ib]) == 0):
                print("WARNING : remainder in integer division")
                
            all_shiftsUn[il,ib] = ((-TimeRevsUn[il,ib]*nint*TimeShiftNumUn[il,ib]) // TimeShiftDenUn[il,ib] ) % nint
        
    for iint in range(nint):

        for il in range(nloop):
            for ib in range(loopnb[il]):
                for idim in range(ndim):
                    
                    b = SpaceRotsUn[il,ib,idim,0]*all_acc[il,0,all_shiftsUn[il,ib]]
                    for jdim in range(1,ndim):  
                        b += SpaceRotsUn[il,ib,idim,jdim]*all_acc[il,jdim,all_shiftsUn[il,ib]]                  

                    all_Newt_err[Targets[il,ib],idim,iint] -= mass[Targets[il,ib]]*b

        # Different loops
        for il in range(nloop):
            for ilp in range(il+1,nloop):

                for ib in range(loopnb[il]):
                    for ibp in range(loopnb[ilp]):
                        
                        prod_mass = mass[Targets[il,ib]]*mass[Targets[ilp,ibp]]

                        for idim in range(ndim):
                            dx[idim] = SpaceRotsUn[il,ib,idim,0]*all_pos[il,0,all_shiftsUn[il,ib]] - SpaceRotsUn[ilp,ibp,idim,0]*all_pos[ilp,0,all_shiftsUn[ilp,ibp]]
                            for jdim in range(1,ndim):
                                dx[idim] += SpaceRotsUn[il,ib,idim,jdim]*all_pos[il,jdim,all_shiftsUn[il,ib]] - SpaceRotsUn[ilp,ibp,idim,jdim]*all_pos[ilp,jdim,all_shiftsUn[ilp,ibp]]

                        dx2 = dx[0]*dx[0]
                        for idim in range(1,ndim):
                            dx2 += dx[idim]*dx[idim]
                            
                        pot,potp,potpp = CCpt_interbody_pot(dx2)
                        
                        a = (2*prod_mass*potp)

                        for idim in range(ndim):
                                
                            b = a*dx[idim]
                            all_Newt_err[Targets[il ,ib ],idim,iint] += b
                            all_Newt_err[Targets[ilp,ibp],idim,iint] -= b

        # Same Loop
        for il in range(nloop):

            for ib in range(loopnb[il]):
                for ibp in range(ib+1,loopnb[il]):
                    
                    prod_mass = mass[Targets[il,ib]]*mass[Targets[il,ibp]]

                    for idim in range(ndim):
                        dx[idim] = SpaceRotsUn[il,ib,idim,0]*all_pos[il,0,all_shiftsUn[il,ib]] - SpaceRotsUn[il,ibp,idim,0]*all_pos[il,0,all_shiftsUn[il,ibp]]
                        for jdim in range(1,ndim):
                            dx[idim] += SpaceRotsUn[il,ib,idim,jdim]*all_pos[il,jdim,all_shiftsUn[il,ib]] - SpaceRotsUn[il,ibp,idim,jdim]*all_pos[il,jdim,all_shiftsUn[il,ibp]]
                    
                    dx2 = dx[0]*dx[0]
                    for idim in range(1,ndim):
                        dx2 += dx[idim]*dx[idim]
                        
                    pot,potp,potpp = CCpt_interbody_pot(dx2)
                    
                    a = (2*prod_mass*potp)

                    for idim in range(ndim):
                        
                        b = a*dx[idim]
                        all_Newt_err[Targets[il,ib] ,idim,iint] += b
                        all_Newt_err[Targets[il,ibp],idim,iint] -= b

        # Increments time at the end
        for il in range(nloop):
            for ib in range(loopnb[il]):
                all_shiftsUn[il,ib] = (all_shiftsUn[il,ib]+TimeRevsUn[il,ib]) % nint
                
    return all_Newt_err


