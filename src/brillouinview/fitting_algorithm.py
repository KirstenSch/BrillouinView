import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import find_peaks


def gaussian(x, amplitude, center, sigma):
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
        'params': list of dicts with 'amplitude', 'center', 'sigma' for each peak
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
    
    # Extract baseline and parameters for each peak
    baseline = popt[0]
    peak_params = []
    
    for i in range(1, len(popt), 3):
        peak_params.append({
            'amplitude': popt[i],
            'center': popt[i + 1],
            'sigma': popt[i + 2],
            'fwhm': 2.355 * popt[i + 2],  # Full Width at Half Maximum
            'area': popt[i] * popt[i + 2] * np.sqrt(2 * np.pi)  # Integral of Gaussian
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
        'baseline': baseline,
        'fitted_curve': fitted_curve,
        'x_values': x,
        'residuals': residuals,
        'r_squared': r_squared,
        'covariance': pcov
    }