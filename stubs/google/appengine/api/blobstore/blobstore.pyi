from typing import Any

BlobKey: Any
BLOB_INFO_KIND: str
BLOB_KEY_HEADER: str
BLOB_MIGRATION_KIND: str
BLOB_RANGE_HEADER: str
MAX_BLOB_FETCH_SIZE: Any
GS_PREFIX: str
UPLOAD_INFO_CREATION_HEADER: str
CLOUD_STORAGE_OBJECT_HEADER: str

class Error(Exception): ...
class InternalError(Error): ...
class BlobNotFoundError(Error): ...
class DataIndexOutOfRangeError(Error): ...
class BlobFetchSizeTooLargeError(Error): ...
class _CreationFormatError(Error): ...
class PermissionDeniedError(Error): ...

def create_rpc(deadline: Any | None = ..., callback: Any | None = ...): ...
def create_upload_url(success_path, max_bytes_per_blob: Any | None = ..., max_bytes_total: Any | None = ..., rpc: Any | None = ..., gs_bucket_name: Any | None = ...): ...
def create_upload_url_async(success_path, max_bytes_per_blob: Any | None = ..., max_bytes_total: Any | None = ..., rpc: Any | None = ..., gs_bucket_name: Any | None = ...): ...
def delete(blob_keys, rpc: Any | None = ..., _token: Any | None = ...): ...
def delete_async(blob_keys, rpc: Any | None = ..., _token: Any | None = ...): ...
def fetch_data(blob_key, start_index, end_index, rpc: Any | None = ...): ...
def fetch_data_async(blob_key, start_index, end_index, rpc: Any | None = ...): ...
def create_gs_key(filename, rpc: Any | None = ...): ...
def create_gs_key_async(filename, rpc: Any | None = ...): ...
