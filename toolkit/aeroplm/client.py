import requests
import hashlib
import os

class AeroClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.token = None

    def create_item(self, item_id: str, name: str, item_type: str = "PART"):
        payload = {
            "item_id": item_id,
            "name": name,
            "item_type": item_type
        }
        response = requests.post(f"{self.base_url}/api/v1/items/", json=payload)
        response.raise_for_status()
        return response.json()

    def upload_file(self, revision_id: str, filepath: str):
        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            files = {"file": (filename, f)}
            response = requests.post(
                f"{self.base_url}/api/v1/vault/upload/{revision_id}",
                files=files
            )
        response.raise_for_status()
        return response.json()

    def process_fea(self, file_id: str):
        response = requests.post(f"{self.base_url}/api/v1/fea/process/{file_id}")
        response.raise_for_status()
        return response.json()

    def promote_revision(self, revision_id: str):
        response = requests.post(f"{self.base_url}/api/v1/workflow/promote/{revision_id}")
        response.raise_for_status()
        return response.json()
