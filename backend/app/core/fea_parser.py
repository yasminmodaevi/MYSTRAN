import re

def parse_nastran_f06(file_content: str):
    """
    Parses a Nastran .f06 file for key engineering metrics.
    """
    results = {
        "max_displacement": None,
        "max_stress": None,
        "margin_of_safety": None
    }

    # Simple regex search for demonstration
    # In real Nastran files, these are found in specific tables
    disp_match = re.search(r"MAXIMUM\s+DISPLACEMENT\s+=\s+([\d.E+-]+)", file_content)
    if disp_match:
        results["max_displacement"] = float(disp_match.group(1))

    stress_match = re.search(r"MAXIMUM\s+STRESS\s+=\s+([\d.E+-]+)", file_content)
    if stress_match:
        results["max_stress"] = float(stress_match.group(1))

    return results
