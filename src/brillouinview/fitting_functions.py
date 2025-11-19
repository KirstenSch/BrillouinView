# This module defines various fitting functions commonly used in spectral analysis.

import numpy as np
from scipy.special import wofz
from tkinter import messagebox  

def gaussian(x, amp, mean, stddev):
    # Define the Gaussian fitting function
    return amp * np.exp(-(x - mean)**2 / (2 * stddev**2))

def lorentzian(x, amp, mean, gamma):
    # Define the Lorentzian fitting function
    return amp * (gamma**2) / ((x - mean)**2 + gamma**2)

def voigt(x, amp, mean, stddev, gamma):
    # Define the Voigt fitting function
    z = (x - mean + 1j * gamma) / (stddev * np.sqrt(2))
    denominator = stddev * np.sqrt(2 * np.pi)
    if np.any(np.abs(denominator) < 1e-10):
        #print("Division by zero or small denominator encountered.")
        messagebox.showerror("Error", "Division by zero or small denominator encountered.")
        voigt_profile = np.zeros_like(x)
    else:
        wofz_result = wofz(z)
        voigt_profile = amp * np.real(wofz_result / denominator)
        
    return voigt_profile

def pseudo_voigt(x, amp, mean, stddev, fraction):
    # Define the Pseudo-Voigt fitting function
    return fraction * lorentzian(x, amp, mean, stddev) + (1 - fraction) * gaussian(x, amp, mean, stddev)

def _2gaussian(x, amp1, mean1, stddev1, amp2, mean2, stddev2):
    # Define the double Gaussian fitting function
    return amp1 * np.exp(-(x - mean1)**2 / (2 * stddev1**2)) + amp2 * np.exp(-(x - mean2)**2 / (2 * stddev2**2)) 

def _2lorentzian(x, amp1, mean1, gamma1, amp2, mean2, gamma2):
    # Define the double Lorentzian fitting function
    return amp1 * (gamma1**2) / ((x - mean1)**2 + gamma1**2) + amp2 * (gamma2**2) / ((x - mean2)**2 + gamma2**2)

def _2voigt(x, amp1, mean1, stddev1, gamma1, amp2, mean2, stddev2, gamma2):
    # Define the double Voigt fitting function
    z1 = (x - mean1 + 1j * gamma1) / (stddev1 * np.sqrt(2))
    z2 = (x - mean2 + 1j * gamma2) / (stddev2 * np.sqrt(2))
    denominator1 = stddev1 * np.sqrt(2 * np.pi)
    denominator2 = stddev2 * np.sqrt(2 * np.pi)

    if np.any(np.abs(denominator1) < 1e-10) or np.any(np.abs(denominator2) < 1e-10):
        #print("Division by zero or small denominator encountered.")
        messagebox.showerror("Error", "Division by zero or small denominator encountered.")
        voigt_profile = np.zeros_like(x)
    else:
        wofz_result1 = wofz(z1)
        wofz_result2 = wofz(z2)
        voigt_profile = (amp1 * np.real(wofz_result1 / denominator1) +
                         amp2 * np.real(wofz_result2 / denominator2))
        
    return voigt_profile

def _2pseudovoigt(x, amp1, mean1, stddev1, fraction1, amp2, mean2, stddev2, fraction2):
    # Define the double Pseudo-Voigt fitting function
    return fraction1 * lorentzian(x, amp1, mean1, stddev1) + (1 - fraction1) * gaussian(x, amp1, mean1, stddev1) + fraction2 * lorentzian(x, amp2, mean2, stddev2) + (1 - fraction2) * gaussian(x, amp2, mean2, stddev2)
