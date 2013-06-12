"""
utils.py - Simple utilility funtions used in pyquante2.

 Copyright (c) 2004, Richard P. Muller. All Rights Reserved. 

 PyQuante version 2.0 and later is covered by the GPL
 license. Please see the file LICENSE that is part of this
 distribution. 
"""
import numpy as np
from math import factorial,gamma,lgamma
from itertools import combinations_with_replacement

def pairs(it): return combinations_with_replacement(it,2)

def isnear(a,b,tol=1e-9): return abs(a-b)<tol

def fact2(n):
    """
    fact2(n) - n!!, double factorial of n
    >>> fact2(0)
    1
    >>> fact2(1)
    1
    >>> fact2(3)
    3
    >>> fact2(8)
    384
    >>> fact2(-1)
    1
    """
    return reduce(int.__mul__,xrange(n,0,-2),1)

def norm2(a): return np.dot(a,a)

def binomial(n,k):
    """
    Binomial coefficient
    >>> binomial(5,2)
    10
    >>> binomial(10,5)
    252
    """
    if n==k: return 1
    assert n>k, "Attempting to call binomial(%d,%d)" % (n,k)
    return factorial(n)/(factorial(k)*factorial(n-k))

def Fgamma(m,x):
    """
    Incomplete gamma function
    >>> round(Fgamma(0,0),10)
    1.0
    """
    SMALL=1e-12
    x = max(x,SMALL)
    return 0.5*pow(x,-m-0.5)*gamm_inc(m+0.5,x)

def gamm_inc(a,x):
    """
    Incomple gamma function \gamma; computed from NumRec routine gammp.
    """
    gammap,gln = gammp(a,x)
    return np.exp(gln)*gammap
    
def gammp(a,x):
    "Returns the incomplete gamma function P(a;x). NumRec sect 6.2."
    assert (x > 0 and a >= 0), "Invalid arguments in routine gammp: %s,%s" % (x,a)

    if x < (a+1.0): #Use the series representation
        gamser,gln = _gser(a,x)
        return gamser,gln
    #Use the continued fraction representation
    gammcf,gln = _gcf(a,x)
    return 1.0-gammcf ,gln  #and take its complement.

def _gser(a,x):
    "Series representation of Gamma. NumRec sect 6.1."
    ITMAX=100
    EPS=3.e-7

    gln=lgamma(a)
    assert(x>=0),'x < 0 in gser'
    if x == 0 : return 0,gln

    ap = a
    delt = sum = 1./a
    for i in xrange(ITMAX):
        ap=ap+1.
        delt=delt*x/ap
        sum=sum+delt
        if abs(delt) < abs(sum)*EPS: break
    else:
        print 'a too large, ITMAX too small in gser'
    gamser=sum*np.exp(-x+a*np.log(x)-gln)
    return gamser,gln

def _gcf(a,x):
    "Continued fraction representation of Gamma. NumRec sect 6.1"
    ITMAX=100
    EPS=3.e-7
    FPMIN=1.e-30

    gln=lgamma(a)
    b=x+1.-a
    c=1./FPMIN
    d=1./b
    h=d
    for i in xrange(1,ITMAX+1):
        an=-i*(i-a)
        b=b+2.
        d=an*d+b
        if abs(d) < FPMIN: d=FPMIN
        c=b+an/c
        if abs(c) < FPMIN: c=FPMIN
        d=1./d
        delt=d*c
        h=h*delt
        if abs(delt-1.) < EPS: break
    else:
        print 'a too large, ITMAX too small in gcf'
    gammcf=np.exp(-x+a*np.log(x)-gln)*h
    return gammcf,gln

def trace2(A,B):
    "Return trace(AB) of matrices A and B"
    return sum(A*B)

def dmat(c,nocc):
    "Form the density matrix from the first nocc orbitals of c"
    return np.dot(c[:,:nocc],c[:,:nocc].T)

def simx(A,B):
    "Similarity transform B^TAB"
    return np.dot(B.T,dot(A,B))

def geigh(H,S):
    "Solve the generalized eigensystem Hc = ESc"
    X = np.inv(np.cholesky(S)).T
    E,U = np.eigh(simx(H,X))
    return E,dot(X,U)
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()

