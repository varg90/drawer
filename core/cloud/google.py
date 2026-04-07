from core.cloud.base import CloudProvider

class GoogleDriveProvider(CloudProvider):
    name = "google"
    def list_files(self, url):
        raise NotImplementedError
    def download(self, cloud_file, dest_path):
        raise NotImplementedError
