'''
Choreo_scipy_plus.py : Define things I designed I feel ought to be in scipy.

'''

import numpy as np
import math as m
import scipy.optimize
import scipy.linalg as la
import scipy.sparse as sp
import functools

def nonlin_solve_pp(
        F,
        x0,
        jacobian='krylov',
        iter=None,
        verbose=False,
        maxiter=None,
        f_tol=None,
        f_rtol=None,
        x_tol=None,
        x_rtol=None,
        tol_norm=None,
        line_search='armijo',
        callback=None,
        full_output=False,
        raise_exception=True
    ):
    """
    Patched version of scipy's nonlin_solve.

    """
    # Can't use default parameters because it's being explicitly passed as None
    # from the calling function, so we need to set it here.
    tol_norm = scipy.optimize.nonlin.maxnorm if tol_norm is None else tol_norm
    condition = scipy.optimize.nonlin.TerminationCondition(f_tol=f_tol, f_rtol=f_rtol,x_tol=x_tol, x_rtol=x_rtol,iter=iter, norm=tol_norm)

    x0 = _as_inexact_pp(x0)
    func = lambda z: _as_inexact_pp(F(_array_like_pp(z, x0))).flatten()
    x = x0.flatten()

    dx = np.full_like(x, np.inf)
    Fx = func(x)
    Fx_norm = np.linalg.norm(Fx)

    jacobian = scipy.optimize.nonlin.asjacobian(jacobian)
    jacobian.setup(x.copy(), Fx, func)

    if maxiter is None:
        if iter is not None:
            maxiter = iter + 1
        else:
            maxiter = 100*(x.size+1)

    if line_search is True:
        line_search = 'armijo'
    elif line_search is False:
        line_search = None

    if line_search not in (None, 'armijo', 'wolfe'):
        raise ValueError("Invalid line search")

    # Solver tolerance selection ===> ???? What are those ?
    gamma = 0.9
    eta_max = 0.9999
    eta_treshold = 0.1
    eta = 1e-3

    for n in range(maxiter):
        status = condition.check(Fx, x, dx)
        if status:
            break

        # The tolerance, as computed for scipy.sparse.linalg.* routines
        tol = min(eta, eta*Fx_norm)
        dx = -jacobian.solve(Fx, tol=tol)

        if np.linalg.norm(dx) == 0:
            raise ValueError("Jacobian inversion yielded zero vector. "
                             "This indicates a bug in the Jacobian "
                             "approximation.")

        # Line search, or Newton step
        if line_search:
            s, x, Fx, Fx_norm_new = _nonlin_line_search_pp(func, x, Fx, dx,line_search)
        else:
            s = 1.0
            x = x + dx
            Fx = func(x)
            Fx_norm_new = np.linalg.norm(Fx)

        jacobian.update(x.copy(), Fx)

        if callback:
            callback(x, Fx)

        # Adjust forcing parameters for inexact methods
        eta_A = gamma * Fx_norm_new**2 / Fx_norm**2
        if gamma * eta**2 < eta_treshold:
            eta = min(eta_max, eta_A)
        else:
            eta = min(eta_max, max(eta_A, gamma*eta**2))

        Fx_norm = Fx_norm_new

        # Print status
        if verbose:
            sys.stdout.write("%d:  |F(x)| = %g; step %g\n" % (
                n, tol_norm(Fx), s))
            sys.stdout.flush()
    else:
        if raise_exception:
            raise NoConvergence(_array_like_pp(x, x0))
        else:
            status = 2

    if full_output:
        info = {'nit': condition.iteration,
                'fun': Fx,
                'status': status,
                'success': status == 1,
                'message': {1: 'A solution was found at the specified '
                               'tolerance.',
                            2: 'The maximum number of iterations allowed '
                               'has been reached.'
                            }[status]
                }
        return _array_like_pp(x, x0), info
    else:
        return _array_like_pp(x, x0)




def _as_inexact_pp(x):
    """Return `x` as an array, of either floats or complex floats"""
    x = np.asarray(x)
    if not np.issubdtype(x.dtype, np.inexact):
        return np.asarray(x, dtype=np.float_)
    return x

def _array_like_pp(x, x0):
    """Return ndarray `x` as same array subclass and shape as `x0`"""
    x = np.reshape(x, np.shape(x0))
    wrap = getattr(x0, '__array_wrap__', x.__array_wrap__)
    return wrap(x)


def _safe_norm_pp(v):
    if not np.isfinite(v).all():
        return np.array(np.inf)
    return np.linalg.norm(v)

def _nonlin_line_search_pp(func, x, Fx, dx, search_type='armijo', rdiff=1e-8, smin=1e-2):

    tmp_s = [0]
    tmp_Fx = [Fx]
    tmp_phi = [np.linalg.norm(Fx)**2]
    s_norm = np.linalg.norm(x) / np.linalg.norm(dx)

    def phi(s, store=True):
        if s == tmp_s[0]:
            return tmp_phi[0]
        xt = x + s*dx
        v = func(xt)
        p = _safe_norm_pp(v)**2
        if store:
            tmp_s[0] = s
            tmp_phi[0] = p
            tmp_Fx[0] = v
        return p

    def derphi(s):
        ds = (abs(s) + s_norm + 1) * rdiff
        return (phi(s+ds, store=False) - phi(s)) / ds

    if search_type == 'wolfe':
        s, phi1, phi0 = scipy.optimize.nonlin.scalar_search_wolfe1(phi, derphi, tmp_phi[0], xtol=1e-2, amin=smin)
    elif search_type == 'armijo':
        s, phi1 = scipy.optimize.nonlin.scalar_search_armijo(phi, tmp_phi[0], -tmp_phi[0], amin=smin)

    if s is None:
        # XXX: No suitable step length found. Take the full Newton step,
        #      and hope for the best.
        s = 1.0

    x = x + s*dx
    if s == tmp_s[0]:
        Fx = tmp_Fx[0]
    else:
        Fx = func(x)
    Fx_norm = np.linalg.norm(Fx)

    return s, x, Fx, Fx_norm
