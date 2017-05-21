#!/usr/bin/env python
"""\
mcscf.py - multiconfigurational self-consistent field methods

The methods defined in this module seek to optimize a set of orbitals
with the energy expression:

  E = 2 f_i h_ii + a_ij J_ij + b_ij K_ij

Here
  f_i   Occupations of orbital i
  a_ij  Coulombic coefficient for orbitals i,j
  b_ij  Exchange coefficient for orbitals i,j

  h_ij  One electron Hamiltonian
        Sum of kinetic t_ij and nuclear attraction v_ij terms
  J_ij  Coulomb interaction between orbitals i,j
  K_ij  Exchange interaction between orbitals i,j

  i,j   indices of orbitals
  m,n   indices of basis functions

With different choices for the f,a,b terms, this energy expression can
describe
  - Closed shell RHF
  - Open shell ROHF
  - Generalized valence bond MC-SCF
  - More general MC-SCFs, CAS-SCF, etc.
We will start with the first three of these, and generalize to the fourth
when all is working with those.

A good reference to the general method is:
The Self-Consistent Equations for Generalized Valence Bond and Open-Shell
Hartree-Fock Wave Functions
Frank W. Bobrowicz and William A. Goddard, III, in
Methods of Electronic Structure Theory, H.F. Schaeffer, III, ed.
Plenum Publishing Corp., 1977
http://www.wag.caltech.edu/publications/sup/pdf/108.pdf

For RHF, ROHF, and GVB wave functions, the f,a,b terms take a fairly
simple form:

  f_i = 1      If the orbital is closed-shell (doubly occupied)
  f_i = 1/2    If the orbital is open-shell (singly-occupied, high spin)
  f_i = c_i^2  If the orbital is part of a GVB pair with coefficient c_i

  a_ij = 2 f_i f_j
  b_ij = -f_i f_j

except that:
  b_ij = -1/2               If i and j are both open-shell
  a_ii = f_i, b_ii = 0      If i is a pair orbital
  a_ij = 0, b_ij = -c_i c_j If i and j are in the same pair

"""
import numpy as np
from pyquante2.geo.samples import h2o,lih,oh,li
from pyquante2.basis.basisset import basisset
from pyquante2.utils import trace2,geigh,dmat
from pyquante2.ints.integrals import onee_integrals, twoe_integrals
from pyquante2.ints.two import ERI

def rhf(geo,basisname='sto3g',maxiter=25,verbose=False):
    """\
    This is a trivial test for the mcscf module, because other
    pyquante modules are simpler if you're doing closed shell rhf,
    and should give the same results.
    """
    # Get the basis set and the integrals
    bfs = basisset(geo,basisname)
    i1 = onee_integrals(bfs,geo)
    i2 = twoe_integrals(bfs)
    h = i1.T + i1.V

    # Get a guess for the orbitals
    E,U = geigh(h,i1.S)

    # Set the parameters based on the molecule
    nopen = geo.nopen()
    assert nopen == 0
    npair = 0
    ncore = geo.nclosed() - npair
    nocc = ncore + nopen + 2*npair
    norb = len(bfs)
    virt = range(nocc,norb)
    orbs_per_shell = get_orbs_per_shell(ncore,nopen,npair)
    nsh = len(orbs_per_shell)
    shells = orbital_to_shell_mapping(ncore,nopen,npair)
    
    f,a,b = fab(ncore,nopen,npair)

    Eold = 0
    for it in range(maxiter):
        # Make all of the density matrices:
        Ds = [dmat_gen(U,orbs) for orbs in orbs_per_shell]
        # Make the 2e matrices
        Js = [i2.get_j(D) for D in Dmats]
        Ks = [i2.get_j(K) for D in Dmats]
        # Make the Fock matrices
        Fs = [f[i]*h + sum(a[i,j]*Js[j] + b[i,j]*Ks[j] for j in range(nsh))
              for i in range(nsh)]

        # Compute the one-electron part of the energy
        hmo = ao2mo(h,U)
        Eone = sum(f[shell[i]]*hmo[i,i] for i in range(nocc))

        # Perform the OCBSE step
        E = Eone
        Unew = np.zeros(U.shape,'d') # We'll put the new orbitals here
        for i,orbs in enumerate(orbs_per_shell):
            space = orbs + virts
            F = ao2mo(H,U[:,space])
            Ei,C = eigh(F)
            E += sum(Ei[orbs])
            Ui = np.dot(C.T,U[:,space])
            Unew[:,space] = Ui
        U = Unew

        # Perform the ROTION step:

        
        print("Iteration %d: Energy %.2f" % (it,E))
        if np.isclose(E,Eold):
            print("Energy converged")
            break
    else:
        print("Maximum iterations (%d) reached without convergence" % (maxit))
    return

def orbital_to_shell_mapping(ncore,nopen,npair):
    """\
    Map the orbitals to shells. All the core orbitals are in
    the first shell. Then each orbital has its own shell.
    >>> orbital_to_shell_mapping(1,0,0)
    [0]
    >>> orbital_to_shell_mapping(2,0,0)
    [0, 0]
    >>> orbital_to_shell_mapping(2,1,0)
    [0, 0, 1]
    """
    shell = [0 for i in range(ncore)]
    ncoreshells = 1 if ncore else 0
    for i in range(nopen+2*npair):
        shell.append(i+ncoreshells)
    return shell

def dmat_gen(c,indices): return np.dot(c[:,indices],c[:,indices].T)

def get_orbs_per_shell(ncore,nopen,npair):
    nocc = ncore+nopen+2*npair
    orbs_per_shell = []
    if ncore:
        orbs_per_shell.append(range(ncore))
    for i in range(ncore,nocc):
        orbs_per_shell.append([i])
    return orbs_per_shell

def guess_gvb_ci_coeffs(npair):
    """
    Make a guess at the CI coefficients for the GVB pairs.
    The orbitals are ordered:
      (pair 1, natural orbital 1),
      (pair 1, natural orbital 2),
      (pair 2, natural orbital 1),
      (pair 2, natural orbital 2),
      ...
    >>> guess_gvb_ci_coeffs(1)
    array([ 1.,  0.])
    >>> guess_gvb_ci_coeffs(2)
    array([ 1.,  0.,  1.,  0.])
    """
    coeffs = []
    for i in range(npair):
        coeffs.append(1)
        coeffs.append(0)
    return np.array(coeffs,'d')

def fab(ncore,nopen,npair,coeffs=None):
    """\
    Create arrays over shells for the coefficients of the
    energy expression:
      E = 2 f_i h_ii + a_ij J_ij + b_ij K_ij
    Here
      f_i   Occupations of orbital i
      a_ij  Coulombic coefficient for orbitals i,j
      b_ij  Exchange coefficient for orbitals i,j

    Shells in GVB are a little confusing. All core orbitals are
    in a single shell, and then each occupied orbital has its own
    shell.
    
    >>> f,a,b = fab(1,0,0)
    >>> f
    array([ 1.])
    >>> a
    array([[ 2.]])
    >>> b
    array([[-1.]])
    >>> f,a,b = fab(0,1,0)
    >>> f
    array([ 0.5])
    >>> a
    array([[ 0.5]])
    >>> b
    array([[-0.5]])
    >>> f,a,b = fab(0,0,1)
    >>> f
    array([ 1.,  0.])
    >>> a
    array([[ 1.,  0.],
           [ 0.,  0.]])
    >>> b
    array([[ 0., -0.],
           [-0.,  0.]])
    """
    ncoresh = 1 if ncore else 0
    nsh = ncoresh+nopen+2*npair
    f = np.zeros(nsh,'d')
    a = np.zeros((nsh,nsh),'d')
    b = np.zeros((nsh,nsh),'d')

    if npair > 0 and coeffs is None:
        coeffs = guess_gvb_ci_coeffs(npair)

    # f array
    if ncore:
        f[0] = 1
    for i in range(nopen):
        f[ncoresh+i] = 0.5

    # This is a little tricky:
    # Assume that the coeffs are arranged p1n1,p1n2,p2n1,p2n2,...
    # But the orbitals are arranged by occupation, p1n1,p2n1,...,p1n2,p2n2,...
    # I may rethink this -- seems unnaturally complex
    for p in range(npair):
        i = ncoresh+nopen+p
        f[i] = coeffs[2*p]
        f[i+npair] = coeffs[2*p+1]

    # Basic a,b assumptions:
    for i in range(nsh):
        for j in range(nsh):
            a[i,j] = 2*f[i]*f[j]
            b[i,j] = -f[i]*f[j]
            
    # Corrections
    # b_ij = -1/2               If i and j are both open-shell
    for i in range(ncoresh,ncoresh+nopen):
        for j in range(ncoresh,ncoresh+nopen):
            b[i,j] = -0.5
    # a_ii = f_i, b_ii = 0      If i is a pair orbital
    for i in range(ncoresh+nopen,ncoresh+nopen+2*npair):
        a[i,i] = f[i]
        b[i,i] = 0
    # a_ij = 0, b_ij = -c_i c_j If i and j are in the same pair
    for i in range(ncoresh+nopen,ncoresh+nopen+npair):
        a[i,i+npair] = a[i+npair,i] = 0
        b[i,i+npair] = b[i+npair,i] = -coeffs[i]*coeffs[i+npair]
    return f,a,b
    
if __name__ == '__main__':
    import doctest; doctest.testmod()