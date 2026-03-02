"""Patch Azure CLI ACR module to respect AZURE_CLI_DISABLE_CONNECTION_VERIFICATION
when uploading build context and streaming logs via BlobClient.

Without this, `az acr build` fails with SSL errors behind a TLS-intercepting proxy.
"""
import glob

patches = [
    (
        "/opt/az/lib/python*/site-packages/azure/cli/command_modules/acr/_archive_utils.py",
        "BlobClient = BlobClient.from_blob_url(upload_url, connection_timeout=300)",
        "from azure.cli.core.util import should_disable_connection_verify\n"
        "    BlobClient = BlobClient.from_blob_url(upload_url, connection_timeout=300,"
        " connection_verify=not should_disable_connection_verify())",
    ),
    (
        "/opt/az/lib/python*/site-packages/azure/cli/command_modules/acr/_stream_utils.py",
        "blob_client = BlobClient.from_blob_url(log_file_sas)",
        "from azure.cli.core.util import should_disable_connection_verify\n"
        "        connection_verify = not should_disable_connection_verify()\n"
        "        blob_client = BlobClient.from_blob_url(log_file_sas,"
        " connection_verify=connection_verify)",
    ),
]

for pattern, old, new in patches:
    for filepath in glob.glob(pattern):
        content = open(filepath).read()
        if old in content:
            open(filepath, "w").write(content.replace(old, new))
            print(f"Patched: {filepath}")
        else:
            print(f"Already patched or not found: {filepath}")
