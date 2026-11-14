"""Helpers for working with Hugging Face Hub references, offline."""
from huggingface_hub import HfApi, InferenceEndpointType
from huggingface_hub.hf_api import repo_type_and_id_from_hf_id


def parse(ref):
    repo_type, namespace, name = repo_type_and_id_from_hf_id(ref)
    return {"type": repo_type or "model", "namespace": namespace, "name": name}


def private_endpoint_kinds():
    return [InferenceEndpointType.PROTECTED.value, InferenceEndpointType.PRIVATE.value]



def has_large_upload():
    return callable(getattr(HfApi(), "upload_large_folder"))
