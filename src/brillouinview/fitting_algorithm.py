import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import find_peaks
from uncertainties import correlated_values, ufloat


def gaussian(x, amplitude:float, center:float, sigma:float):
    """Single Gaussian peak function."""
    return amplitude * np.exp(-((x - center) ** 2) / (2 * sigma ** 2))


def multi_gaussian(x, *params):
    """Multiple Gaussian peaks combined with a constant baseline.
    
    params: flattened list [baseline, amp1, center1, sigma1, amp2, center2, sigma2, ...]
    First parameter is the constant baseline offset.
    """
    baseline = params[0]
    y = np.full_like(x, baseline, dtype=float)
    
    for i in range(1, len(params), 3):
        y += gaussian(x, params[i], params[i + 1], params[i + 2])
    return y



def estimate_initial_params(x, y, n_peaks):
    """Estimate initial parameters for n_peaks Gaussians (dips) with baseline.
    
    Returns: list of [baseline, amp1, center1, sigma1, amp2, center2, sigma2, ...]
    """
    # Estimate baseline as median or percentile of data
    baseline_estimate = np.percentile(y, 75)  # Assume baseline is near upper values
    
    # Subtract baseline to find dips
    y_corrected = y - baseline_estimate
    
    # Find dips (local minima) by inverting the signal
    peaks, properties = find_peaks(-y_corrected, prominence=np.std(y) * 0.5, width=1)
    
    # Sort by prominence and take top n_peaks
    if len(peaks) > n_peaks:
        prominences = properties['prominences']
        top_indices = np.argsort(prominences)[-n_peaks:]
        peaks = peaks[top_indices]
    
    # If we found fewer peaks than requested, add evenly spaced guesses
    if len(peaks) < n_peaks:
        extra_needed = n_peaks - len(peaks)
        # Add peaks at regular intervals where we haven't found any
        x_range = x.max() - x.min()
        spacing = x_range / (n_peaks + 1)
        for i in range(extra_needed):
            new_center = x.min() + spacing * (i + 1)
            peaks = np.append(peaks, np.argmin(np.abs(x - new_center)))
    
    # Build initial parameters starting with baseline
    initial_params = [baseline_estimate]
    
    for peak_idx in peaks:
        amplitude = y_corrected[peak_idx]  # Will be negative for dips
        center = x[peak_idx]
        # Estimate sigma from peak width (rough approximation)
        sigma = (x.max() - x.min()) / (n_peaks * 4)  # reasonable default
        initial_params.extend([amplitude, center, sigma])
    
    return initial_params


def fit_peaks(df, n_peaks, column='intensities'):
    """Fit n_peaks Gaussian peaks to spectroscopic data.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with index as x-values and intensity column
    n_peaks : int
        Number of peaks to fit
    column : str
        Name of the intensity column (default: 'intensities')
    
    Returns:
    --------
    dict with:
        'params': list of dicts with 'amplitude', 'center', 'sigma' for each peak (as ufloats)
        'fitted_curve': array of fitted y-values
        'residuals': array of (observed - fitted)
        'r_squared': coefficient of determination
    """
    # Extract data
    x = df.index.values
    y = df[column].values
    
    # Check for negative values (faulty data)
    if np.any(y < 0):
        negative_indices = np.where(y < 0)[0]
        raise ValueError(
            f"Faulty data detected: {len(negative_indices)} negative intensity values found. "
            f"Please inspect data at indices: {x[negative_indices[:5]].tolist()}"
            + ("..." if len(negative_indices) > 5 else "")
        )
    
    if len(x) < 3 * n_peaks:
        raise ValueError(f"Not enough data points for {n_peaks} peaks")
    
    # Get initial parameter estimates
    p0 = estimate_initial_params(x, y, n_peaks)
    
    # Set reasonable bounds
    # First bound is for baseline
    bounds_lower = [0]  # Baseline >= 0
    bounds_upper = [y.max() * 1.5]  # Baseline can be up to 1.5x max value
    
    # Then bounds for each peak
    for i in range(n_peaks):
        bounds_lower.extend([y.min() - y.max(), x.min(), 0])  # amp can be negative, center in range, sigma>0
        bounds_upper.extend([y.max(), x.max(), x.max() - x.min()])
    
    # Perform the fit
    try:
        popt, pcov = curve_fit(
            multi_gaussian, 
            x, 
            y, 
            p0=p0,
            bounds=(bounds_lower, bounds_upper),
            maxfev=10000
        )
    except RuntimeError as e:
        raise RuntimeError(f"Fitting failed: {e}")
    
    # Build peak parameter ufloats using the uncertainties package.
    peak_params = []
    sqrt2pi = np.sqrt(2 * np.pi)
    
    # Preferred: create correlated ufloats so derived quantities propagate covariance
    try:
        correlated = correlated_values(popt, pcov)
        baseline_u = correlated[0]
        for i in range(1, len(popt), 3):
            amp_u = correlated[i]
            center_u = correlated[i + 1]
            sigma_u = correlated[i + 2]
            fwhm_u = 2.355 * sigma_u
            area_u = amp_u * sigma_u * sqrt2pi
            peak_params.append({
                'amplitude': amp_u,
                'center': center_u,
                'sigma': sigma_u,
                'fwhm': fwhm_u,
                'area': area_u
            })
    except Exception:
        # Fallback: create independent ufloats from sqrt of diagonal of pcov (handle invalid/missing pcov)
        if pcov is None or pcov.size == 0:
            perr = np.full_like(popt, np.nan, dtype=float)
        else:
            with np.errstate(invalid='ignore'):
                diag = np.diag(pcov)
                perr = np.sqrt(np.where(diag >= 0, diag, np.nan))
    
        baseline_u = ufloat(float(popt[0]), float(perr[0]) if perr.size > 0 else np.nan)
        for i in range(1, len(popt), 3):
            amp_u = ufloat(float(popt[i]), float(perr[i]) if perr.size > i else np.nan)
            center_u = ufloat(float(popt[i + 1]), float(perr[i + 1]) if perr.size > (i + 1) else np.nan)
            sigma_u = ufloat(float(popt[i + 2]), float(perr[i + 2]) if perr.size > (i + 2) else np.nan)
            fwhm_u = 2.355 * sigma_u
            area_u = amp_u * sigma_u * sqrt2pi
            peak_params.append({
                'amplitude': amp_u,
                'center': center_u,
                'sigma': sigma_u,
                'fwhm': fwhm_u,
                'area': area_u
            })
    
    # Calculate fitted curve and residuals
    fitted_curve = multi_gaussian(x, *popt)
    residuals = y - fitted_curve
    
    # Calculate R²
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot)
    
    return {
        'params': peak_params,
        'baseline': baseline_u,
        'fitted_curve': fitted_curve,
        'x_values': x,
        'residuals': residuals,
        'r_squared': r_squared,
        'covariance': pcov
    }