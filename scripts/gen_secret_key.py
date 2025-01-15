#!/usr/bin/env python3

import os
import secrets


if __name__ == "__main__":
    secret_key = secrets.token_hex(16)
    filename = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "..", ".env"
    )
    output = f'SECRET_KEY="{secret_key}"' + "\n"
    with open(filename, "w") as f:
        _ = f.write(output)
        print(".env written!")
