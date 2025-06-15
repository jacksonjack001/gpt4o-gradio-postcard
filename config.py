import abc
import os
import configparser
import openai
import logging


class Singleton(abc.ABCMeta, type):
    """
    Singleton metaclass for ensuring only one instance of a class.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """Call method for the singleton metaclass."""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Config(metaclass=Singleton):
    """
    Configuration class to store the state of bools for different scripts access.
    """

    def __init__(self, base_dir="./"):
        """Initialize the Config class"""
        self.debug_mode = False
        self.google_proxy = True
        self.continuous_mode = False
        self.speak_mode = False
        self.robot_online = True

        self.fast_llm_model = os.getenv("FAST_LLM_MODEL", "gpt-3.5-turbo")
        config = configparser.ConfigParser()
        cur_dir = os.path.abspath(__file__)
        base_dir = "/".join(cur_dir.split("/")[:-1])
        config.read(base_dir + "/config/config.ini", encoding="utf-8")

        # oss
        self.oss_access_key_id = config.get("oss", "access_key_id")
        self.oss_access_key_secret = config.get("oss", "access_key_secret")
        self.oss_endpoint = config.get("oss", "endpoint")
        self.oss_bucket_name = config.get("oss", "bucket_name")
        self.oss_dalle_path_dir = config.get("oss", "dalle_path_dir")

        # debug
        self.base_root_dir = base_dir

        # openai
        self.openai_api_base = config.get("openai", "OPENAI_API_BASE")
        self.openai_api_key = config.get("openai", "OPENAI_API_KEY")
        self.COMPLETIONS_MODEL = config.get("openai", "MODEL")

        # zpay
        self.zpay_gateway = config.get("zpay", "GATEWAY")
        self.zpay_pid = config.get("zpay", "PID")
        self.zpay_key = config.get("zpay", "KEY")

        self.env = config.get("environ", "env")
        if self.env == "prod":
            self.pay_callback_host = config.get(
                "pay_callback_host", "pay_callback_host"
            )
        else:
            self.pay_callback_host = config.get(
                "pay_callback_host_dev", "pay_callback_host"
            )

        self.sql_lite_db_file = config.get("db_cfg", "sql_lite_db_file")

        # dashscope-openai
        self.openai_api_base_dashscope = config.get("dashscope", "OPENAI_API_BASE")
        self.openai_api_key_dashscope = config.get("dashscope", "OPENAI_API_KEY")

        # logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(name)-8s %(levelname)-8s %(message)s [%(filename)s:%(lineno)d]"
            )
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def set_continuous_mode(self, value: bool):
        """Set the continuous mode value."""
        self.continuous_mode = value
