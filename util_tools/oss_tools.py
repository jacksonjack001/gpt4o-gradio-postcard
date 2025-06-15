import oss2
import sys
import os

sys.path.insert(-1, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config

config_base = Config()

access_key_id = config_base.oss_access_key_id
access_key_secret = config_base.oss_access_key_secret
endpoint = config_base.oss_endpoint
bucket_name = config_base.oss_bucket_name
auth = oss2.Auth(access_key_id, access_key_secret)
bucket = oss2.Bucket(auth, endpoint, bucket_name)
oss_qn_path_dir = "dalle"


def put_png_to_oss(fpath):
    with open(fpath, "rb") as fileobj:
        oss_file_name = fpath.split("/")[-1]
        bucket.put_object(f"{oss_qn_path_dir}/{oss_file_name}", fileobj)
        res = bucket.put_object_acl(
            f"{oss_qn_path_dir}/{oss_file_name}", oss2.OBJECT_ACL_PUBLIC_READ
        )
        sign_url = bucket.sign_url(
            "POST",
            f"{oss_qn_path_dir}/{oss_file_name}",
            expires=30 * 24 * 60 * 60,
            slash_safe=True,
        )
        file_url = sign_url.split("?")[0]
    return file_url


if __name__ == "__main__":
    res = put_png_to_oss("/data_ext/trae_gradio_gpt4o_img/data/prompt.txt")
    print(res)
