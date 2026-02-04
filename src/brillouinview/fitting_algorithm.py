import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import find_peaks
from scipy.special import wofz
from uncertainties import correlated_values, ufloat


def gaussian(x, amplitude:float, center:float, sigma:float):
    """Single Gaussian peak function."""
    return amplitude * np.exp(-((x - center) ** 2) / (2 * sigma ** 2))


def lorentzian(x, amplitude: float, center: float, gamma: float):
    """Lorentzian peak with peak height = amplitude.
    gamma is the half-width at half-maximum (HWHM).
    """
    x = np.asarray(x, dtype=float)
    # Avoid division by zero; if gamma==0 return a delta-like zero array except at center
    if gamma == 0:
        out = np.zeros_like(x)
        # set exactly at center to amplitude (best-effort)
        idx = np.isclose(x, center)
        out[idx] = amplitude
        return out
    return amplitude * (gamma ** 2 / ((x - center) ** 2 + gamma ** 2))


def voigt(x, amplitude: float, center: float, sigma: float, gamma: float):
    """Voigt profile (convolution of Gaussian(sigma) and Lorentzian(gamma)).
    amplitude scales the peak so value at center equals amplitude.
    sigma: Gaussian standard deviation
    gamma: Lorentzian half-width at half-maximum (HWHM)
    """
    x = np.asarray(x, dtype=float)
    # Handle limiting cases
    if sigma == 0 and gamma == 0:
        out = np.zeros_like(x)
        idx = np.isclose(x, center)
        out[idx] = amplitude
        return out
    if sigma == 0:
        return lorentzian(x, amplitude, center, gamma)
    if gamma == 0:
        return gaussian(x, amplitude, center, sigma)

    # Shift x to center
    x_shift = x - center
    z = (x_shift + 1j * gamma) / (sigma * np.sqrt(2))
    voigt_profile = np.real(wofz(z)) / (sigma * np.sqrt(2 * np.pi))

    # Normalize so center value is 1, then scale by amplitude
    z0 = (1j * gamma) / (sigma * np.sqrt(2))
    center_val = np.real(wofz(z0)) / (sigma * np.sqrt(2 * np.pi))
    if not np.isfinite(center_val) or center_val == 0:
        norm = 1.0
    else:
        norm = center_val
    return amplitude * (voigt_profile / norm)


def pseudo_voigt(x, amplitude: float, center: float, sigma: float, gamma: float, eta: float = None):
    """Pseudo-Voigt approximation: weighted sum of Gaussian and Lorentzian.
    amplitude scales the combined peak (value at center equals amplitude).
    sigma: Gaussian std; gamma: Lorentzian HWHM; eta: mixing parameter [0..1].
    If eta is None an empirical approximation is used.
    """
    x = np.asarray(x, dtype=float)

    # Gaussian component (normalized to 1 at center when sigma>0)
    if sigma > 0:
        gauss = np.exp(-((x - center) ** 2) / (2 * sigma ** 2))
    else:
        gauss = np.zeros_like(x)
        gauss[np.isclose(x, center)] = 1.0

    # Lorentzian component (normalized to 1 at center when gamma>0)
    if gamma > 0:
        lor = gamma ** 2 / ((x - center) ** 2 + gamma ** 2)
    else:
        lor = np.zeros_like(x)
        lor[np.isclose(x, center)] = 1.0

    # Estimate mixing parameter if not provided using common approximation
    if eta is None:
        # FWHMs
        fG = 2 * np.sqrt(2 * np.log(2)) * sigma
        fL = 2 * gamma
        # Combined FWHM approximation (Ida/Thompson style)
        f = (fG ** 5 + 2.69269 * fG ** 4 * fL + 2.42843 * fG ** 3 * fL ** 2
             + 4.47163 * fG ** 2 * fL ** 3 + 0.07842 * fG * fL ** 4 + fL ** 5) ** (1.0 / 5.0)
        if f == 0:
            eta = 0.0
        else:
            fr = fL / f
            eta = 1.36603 * fr - 0.47719 * fr ** 2 + 0.11116 * fr ** 3
            eta = float(np.clip(eta, 0.0, 1.0))

    pv = eta * lor + (1.0 - eta) * gauss
    return amplitude * pv


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

def multi_lorentzian(x, *params):
    """Multiple Lorentzian peaks combined with a constant baseline.

    params: flattened list [baseline, amp1, center1, gamma1, amp2, center2, gamma2, ...]
    First parameter is the constant baseline offset.
    """
    baseline = params[0]
    y = np.full_like(x, baseline, dtype=float)

    for i in range(1, len(params), 4):
        y += lorentzian(x, params[i], params[i + 1], params[i + 2])
    return y

def multi_voigt(x, *params):
    """Multiple Voigt peaks combined with a constant baseline.

    params: flattened list [baseline, amp1, center1, sigma1, gamma1, amp2, center2, sigma2, gamma2, ...]
    First parameter is the constant baseline offset.
    """
    baseline = params[0]
    y = np.full_like(x, baseline, dtype=float)

    for i in range(1, len(params), 4):
        y += voigt(x, params[i], params[i + 1], params[i + 2], params[i + 3])
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