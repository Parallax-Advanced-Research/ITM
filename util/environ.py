import os


def find_environment(var_name: str, default_port: int) -> int:
    port_str = os.getenv(var_name)
    if port_str is None or port_str == "" or not port_str.isnumeric():
        os.environ[var_name] = str(default_port)
        return default_port
    else:
        return int(port_str)