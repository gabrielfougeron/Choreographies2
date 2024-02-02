import os
import sys

__PROJECT_ROOT__ = os.path.abspath(os.path.join(os.path.dirname(__file__),os.pardir))
sys.path.append(__PROJECT_ROOT__)

import pytest
from test_config import *

import numpy as np
import scipy
import choreo



@ProbabilisticTest()
def test_random_orthogonal_matrix(float64_tols, Dense_linalg_dims):

    print("Generation of random orthogonal matrices.")

    for n in Dense_linalg_dims.all_geodims:

        print(f"Dimension: {n}")

        rot = choreo.scipy_plus.linalg.random_orthogonal_matrix(n)

        assert np.allclose(np.matmul(rot  , rot.T), np.identity(n), rtol = float64_tols.rtol , atol = float64_tols.atol) 
        assert np.allclose(np.matmul(rot.T, rot  ), np.identity(n), rtol = float64_tols.rtol , atol = float64_tols.atol) 


@ProbabilisticTest()
def test_nullspace(float64_tols, Dense_linalg_dims):

    print("Testing nullspace of a dense matrix.")

    for n in Dense_linalg_dims.all_geodims:

        for m in Dense_linalg_dims.all_geodims:

            print(f"Dimension: {n}, {m}")

            P = choreo.scipy_plus.linalg.random_orthogonal_matrix(n)

            if (n == m):

                Z = choreo.scipy_plus.linalg.null_space(P)

                assert Z.shape[0] == m
                assert Z.shape[1] == 0

            for rank in range( min(n,m)+1):

                nullspace_dim = min(n,m) - rank

                Q = choreo.scipy_plus.linalg.random_orthogonal_matrix(m)

                diag = np.random.rand(rank)
                diagmat = np.zeros((n,m))

                for i in range(rank):
                    diagmat[i,i] = 2 + diag[i]

                A = np.matmul(P, np.matmul(diagmat, Q))

                Z = choreo.scipy_plus.linalg.null_space(A)

                assert Z.shape[0] == m
                assert Z.shape[1] == nullspace_dim
                assert np.allclose(np.matmul(A,Z), np.zeros((n,nullspace_dim)), rtol = float64_tols.rtol , atol = float64_tols.atol) 











