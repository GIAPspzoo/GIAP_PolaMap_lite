import os
import json
from ..utils import get_project_config, set_project_config

CONFIG_SCOPE = 'WMS_WMTS'
CONFIG_KEY = 'json_file'

def get_wms_config() -> dict:
    current_config = get_project_config(CONFIG_SCOPE, CONFIG_KEY)
    if current_config:
        return json.loads(current_config)
    else:
        json_dict = read_json_file()
        if json_dict:
            return json_dict

def set_wms_config(data: dict) -> None:
    set_project_config(CONFIG_SCOPE, CONFIG_KEY, json.dumps(data))

def get_json_path(json_name: str = 'WMS_WMTS.json') -> str:
    return os.path.join(os.path.dirname(__file__), json_name)

def read_json_file(json_name: str = None) -> dict:
    if json_name is None:
        json_path = get_json_path()
    with open(json_path, "r+") as json_read:
        return json.load(json_read)
