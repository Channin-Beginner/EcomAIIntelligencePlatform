"""Start admin and portal APIs."""

import logging
import multiprocessing
import signal
import sys

import uvicorn

from app.common.logging_config import setup_logging
from app.config import get_settings

logger = logging.getLogger("ecom.runner")


def _run_admin():
    settings = get_settings()
    uvicorn.run(
        "app.admin_app:admin_app",
        host="0.0.0.0",
        port=settings.admin_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


def _run_portal():
    settings = get_settings()
    uvicorn.run(
        "app.portal_app:portal_app",
        host="0.0.0.0",
        port=settings.portal_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


def _stop_processes(*processes: multiprocessing.Process) -> None:
    for proc in processes:
        if proc.is_alive():
            proc.terminate()
    for proc in processes:
        proc.join(timeout=5)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "admin":
            _run_admin()
        elif mode == "portal":
            _run_portal()
        else:
            print("Usage: python run.py [admin|portal]")
            sys.exit(1)
    else:
        setup_logging("runner")
        p1 = multiprocessing.Process(target=_run_admin, daemon=False)
        p2 = multiprocessing.Process(target=_run_portal, daemon=False)
        p1.start()
        p2.start()
        settings = get_settings()
        logger.info("Admin API  http://127.0.0.1:%s", settings.admin_port)
        logger.info("Portal API http://127.0.0.1:%s", settings.portal_port)
        logger.info("Press Ctrl+C to stop both services.")

        def _shutdown(_signum=None, _frame=None) -> None:
            logger.info("Stopping Admin and Portal APIs...")
            _stop_processes(p1, p2)
            sys.exit(0)

        signal.signal(signal.SIGINT, _shutdown)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _shutdown)

        try:
            p1.join()
            p2.join()
        except KeyboardInterrupt:
            _shutdown()
