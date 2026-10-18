"""`python -m app` arranca el servidor con el host y el puerto de la configuración."""

import logging

import uvicorn

from .main import app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(message)s")
    config = app.state.config
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
