## This file duplicates functions from Soartech server so that we can calculate KDE alignment 
## locally, which is non-trivial. Code synced as of 07/29/2024

import numpy as np
from scipy.spatial.distance import jensenshannon
from sklearn.neighbors import KernelDensity
from scipy.integrate import trapezoid

def _normalize_2feature(x, y, z):
    """
    Normalize 2D probability distribution z such that its integral over domain (x, y) is one.

    Parameters
    ----------
    x: ndarray
        domain over which discrete probability distribution z is defined (x-coordinates).
    
    y: ndarray
        domain over which discrete probability distribution z is defined (y-coordinates).

    z: ndarray
        2D probability distribution at each point in (x, y). z is proportional to the
        probability density of the distribution at (x, y).

    Returns
    --------
    pdf: ndarray
        array with same shape as z that gives normalized probability density function
        values at each point (x, y).
    """
    # Compute the area under the surface
    dx = x[1] - x[0]  # assuming uniform spacing
    dy = y[1] - y[0]  # assuming uniform spacing
    area = trapezoid(trapezoid(z, x, axis=0), y, axis=0)
    
    # Normalize z by the computed area
    pdf = z / area

    return pdf

def _kde_to_pdf_2feature(kde, grid_size=100, normalize=True):

    # Create a 2D grid of points within the normalized range [0, 1] x [0, 1]
    x_vals = np.linspace(0, 1, grid_size)
    y_vals = np.linspace(0, 1, grid_size)
    X, Y = np.meshgrid(x_vals, y_vals)
    xy_grid = np.vstack([X.ravel(), Y.ravel()]).T  

    # Evaluate the KDE on the xy_grid
    pf = np.exp(kde.score_samples(xy_grid))
    
    if normalize:
        # Reshape the grid and the probability values
        x_vals = np.linspace(0, 1, grid_size)
        y_vals = np.linspace(0, 1, grid_size)
        pf_reshaped = pf.reshape(grid_size, grid_size)
        
        # Normalize the 2D KDE values
        pf = _normalize_2feature(x_vals, y_vals, pf_reshaped).ravel()
        
    return pf


def js_similarity_2feature(kde1, kde2, grid_size=100):

    # Compute the PDFs of the two 3D KDEs on the 2D grid
    pdf_kde1 = _kde_to_pdf_2feature(kde1, grid_size)
    pdf_kde2 = _kde_to_pdf_2feature(kde2, grid_size)

    js = jensenshannon(pdf_kde1, pdf_kde2)

    # We invert the value because the spec agreed to with the other ITM performs has
    # 0 = unaligned, 1 = full aligned which is the opposite of what Jensenshannon produces. 
    return 1 - js
    
def get_default_2feature_bandwidth(max_value=1.0):
    bandwidth = (max_value / 10) * 0.75 
    return bandwidth
    
def make_2feature_kde(X: list[float], Y: list[float]):
    # Convert input lists to numpy arrays
    X = np.array(X)
    Y = np.array(Y)

    # Concatenate X and Y to form a 2D array where each row is (X[i], Y[i])
    data = np.column_stack((X, Y))

    # Fit Kernel Density Estimation
    kde = KernelDensity(kernel="gaussian", bandwidth=get_default_2feature_bandwidth()).fit(data)

    return kde

def compute_alignment(kdmaLocalEstimates, kdmaGlobalEstimates, targetKde):
    newKde = make_2feature_kde(kdmaLocalEstimates, kdmaGlobalEstimates)
    return js_similarity_2feature(newKde, targetKde)
    