'''
ODE.py : Defines ODE-related things I designed I feel ought to be in scipy.

'''

import numpy as np
import math as m
import mpmath
import functools
import scipy

from choreo.scipy_plus.cython.SegmQuad import IntegrateOnSegment
from choreo.scipy_plus.cython.SegmQuad import QuadFormula

try:
    import numba 
    UseNumba = True
except ImportError:
    UseNumba = False

def SafeGLIntOrder(N):

    n = m.ceil(N/2)

    if (((n%2) == 1) and ((N%2) == 1)) or ((n-1) == N):
        n += 1

    return n

# 3 terms definition of polynomial families
# P_n+1 = (X - a_n) P_n - b_n P_n-1
def GaussLegendre3Term(n):

    a = mpmath.matrix(n,1)
    b = mpmath.matrix(n,1)

    b[0] = 2

    for i in range(1,n):

        i2 = i*i
        b[i] = mpmath.fraction(i2,4*i2-1)

    return a, b

def ShiftedGaussLegendre3Term(n):

    a = mpmath.matrix(n,1)
    b = mpmath.matrix(n,1)

    for i in range(n):
        a[i] = mpmath.fraction(1,2)

    b[0] = 1

    for i in range(1,n):

        i2 = i*i
        b[i] = mpmath.fraction(i2,4*(4*i2-1))

    return a, b

def EvalAllFrom3Term(a,b,n,x):
    # n >= 1

    phi = mpmath.matrix(n+1,1)

    phi[0] = mpmath.mpf(1)
    phi[1] = x - a[0]

    for i in range(1,n):

        phi[i+1] = (x - a[i]) * phi[i] - b[i] * phi[i-1]

    return phi

def EvalAllDerivFrom3Term(a,b,n,x,phi=None):
    # n >= 1

    if phi is None:
        phi = EvalAllFrom3Term(a,b,n,x)

    phip = mpmath.matrix(n+1,1)

    phip[0] = 0
    phip[1] = 1

    for i in range(1,n):

        phip[i+1] = (x - a[i]) * phip[i] - b[i] * phip[i-1] + phi[i]

    return phip

def MatFrom3Term(a,b,n):
    
    J =  mpmath.matrix(n)
    
    for i in range(n):
        J[i,i] = a[i]

    for i in range(n-1):

        J[i  ,i+1] = mpmath.sqrt(b[i+1])
        J[i+1,i  ] = J[i  ,i+1]

    return J

def QuadFrom3Term(a,b,n):

    J = MatFrom3Term(a,b,n)
    z, P = mpmath.mp.eigsy(J)

    w = mpmath.matrix(n,1)
    for i in range(n):
        w[i] = b[0] * P[0,i] * P[0,i]

    return w, z

@functools.cache
def ComputeQuadrature(method,n,dps=30):

    if method == "Gauss" :
        a, b = ShiftedGaussLegendre3Term(n)
        th_cvg_rate = 2*n
        
    else:
        raise ValueError(f"Method not found: {method}")
    
    w, z = QuadFrom3Term(a,b,n)

    w_np = np.array(w.tolist(),dtype=np.float64).reshape(n)
    z_np = np.array(z.tolist(),dtype=np.float64).reshape(n)
    
    return QuadFormula(
        w = w_np                    ,
        x = z_np                    ,
        th_cvg_rate = th_cvg_rate   ,
    )

if UseNumba:
    # Define decorators to make scipy.LowLevelCallable from python functions using numba
    
    default_numba_kwargs = {
        'nopython':True     ,
        'cache':True        ,
        'fastmath':True     ,
        'nogil':True        ,
    }

    def nb_jit_double_double(integrand_function, numba_kwargs = default_numba_kwargs):
        jitted_function = numba.jit(integrand_function, **numba_kwargs)

        #double func(double x)
        @numba.cfunc(numba.types.float64(numba.types.float64))
        def wrapped(x):        
            return jitted_function(x)
        
        return scipy.LowLevelCallable(wrapped.ctypes)

    def nb_jit_array_double(integrand_function, numba_kwargs = default_numba_kwargs):
        jitted_function = numba.jit(integrand_function, **numba_kwargs)

        #func(double x, double * res)
        @numba.cfunc(numba.types.void(numba.types.float64, numba.types.CPointer(numba.types.float64)))
        def wrapped(x, res):   
            res = jitted_function(x)
        
        return scipy.LowLevelCallable(wrapped.ctypes)

    def nb_jit_inplace_double_array(integrand_function, numba_kwargs = default_numba_kwargs):
        jitted_function = numba.jit(integrand_function, **numba_kwargs)

        #func(double x, double * res)
        @numba.cfunc(numba.types.void(numba.types.float64, numba.types.CPointer(numba.types.float64)))
        def wrapped(x, res):   
            jitted_function(x, res)
        
        return scipy.LowLevelCallable(wrapped.ctypes)
