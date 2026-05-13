from aeroplm.client import AeroClient
import sys

def run_stress_analysis_workflow(item_id, f06_path):
    client = AeroClient("http://localhost:8000")

    print(f"--- AeroPLM Stress Analysis Integration ---")

    # 1. Fetch Item (or create if demo)
    try:
        item = client.create_item(item_id, f"Analysis for {item_id}", "DOCUMENT")
        rev_id = item["revisions"][0]["id"]
    except Exception:
        # Assume it exists for this demo
        print("Item exists, fetching revision...")
        # In real app, we'd GET the item
        return

    # 2. Upload Nastran Results
    print(f"Uploading {f06_path} to vault...")
    upload_res = client.upload_file(rev_id, f06_path)
    file_id = upload_res["id"]

    # 3. Extract Metadata (FEA Parsing)
    print("Extracting engineering metrics from Nastran file...")
    analysis = client.process_fea(file_id)
    metrics = analysis["metrics"]
    print(f"Results Extracted: Max Stress = {metrics['max_stress']}, Max Disp = {metrics['max_displacement']}")

    # 4. Promote to Released if within limits
    if metrics["max_stress"] and metrics["max_stress"] < 400.0: # 400 MPa limit example
        print("Design meets requirements. Promoting to RELEASED...")
        client.promote_revision(rev_id)
        print("Status: RELEASED")
    else:
        print("Stress exceeds limits or parsing failed. Design remains IN_WORK.")

if __name__ == "__main__":
    # Example usage: python nastran_connector.py WING_RIB_01 results.f06
    if len(sys.argv) < 3:
        print("Usage: python nastran_connector.py <ITEM_ID> <F06_PATH>")
    else:
        run_stress_analysis_workflow(sys.argv[1], sys.argv[2])
