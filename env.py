import os


def read_env_file():
    filename = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), ".env"
    )
    data: str = ""
    with open(filename, "r") as f:
        data = f.read()

    for s in data.splitlines():
        i = s.find("=")
        name = s[0:i]
        value = s[i + 2 : -1]
        os.environ[name] = value
