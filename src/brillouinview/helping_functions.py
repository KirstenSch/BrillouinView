# Helper: extract nominal value from uncertainties.ufloat-like objects
def nominal(v):
    if v is None:
        return 0.0
    # uncertainties objects expose nominal_value
    if hasattr(v, "nominal_value"):
        try:
            return float(v.nominal_value)
        except Exception:
            pass
    try:
        return float(v)
    except Exception:
        return 0.0