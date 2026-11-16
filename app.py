import os

import uvicorn


def run():
    port = int(os.environ.get("F1_PORT", "8000"))
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port)


if __name__ == "__main__":
    run()
