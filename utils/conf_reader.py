import yaml
import os

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'conf.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            # return json.load(file)
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found at: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error decoding YAML from the config file: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}")