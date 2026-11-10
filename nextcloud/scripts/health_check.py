"""
------------------------------------------------------------------------------
Script Name:      health_check
Script Author:    Neal Russell
Author's Company: N/A
Script Created:   2026-Sep-07
Script Modified:  2026-Sep-07
Script Version:   1.0.0
Script Purpose:   Give Docker a lightweight, internal-only way to confirm
                  log_api_server.py is alive and accepting connections,
                  without exercising the HTTP /logs route, its auth
                  check, or any log file access.

Script Desc:      This script will perform the following actions:
                    * Open a raw TCP connection to 127.0.0.1 on the
                        port log_api_server.py listens on
                    * Exit 0 (success) if the connection opens
                    * Exit 1 (failure) if the connection is refused
                        or times out
                    * Close the connection immediately either way,
                        without sending any data over it

Script Reqs:      Reads LOG_API_PORT from the environment, so it
                  always checks the same port the server itself is
                  configured to listen on, rather than a hardcoded
                  value that could drift out of sync.

Script Notes:     This intentionally does not send an HTTP request or
                  check the /logs route. A bare TCP connect confirms
                  the process is up and listening, which is all
                  'docker container ls -a' needs to report Healthy.
                  Exercising /logs here would mean the healthcheck
                  needs its own bearer token and would touch the same
                  file-read code path on every healthcheck interval,
                  neither of which is necessary just to confirm the
                  process is alive.

------------------------------------------------------------------------------
Execution Context: Docker HEALTHCHECK entrypoint, run via
                   'python3 /app/health_check.py'. Not imported as a
                   module elsewhere.
                   Runtime dependencies: none beyond the Python 3
                   standard library.
------------------------------------------------------------------------------
Change Log:
  1.0.0 - Initial DEV version.
------------------------------------------------------------------------------
To Do List:
  *  None at this time.
------------------------------------------------------------------------------
"""
import os
import socket
import sys



def check_port_open():
    """
    Header comment: Attempts a raw TCP connect to the local log_api_
    server port and reports success or failure via exit code.

    Docstring:
        Uses a short timeout so a hung process is reported as
        unhealthy promptly rather than leaving Docker waiting.
        Any exception during the connection attempt is treated as a
        failed healthcheck, since the specific failure reason
        (refused, timed out, DNS, etc.) does not change what Docker
        should do in response.

    Returns:
        bool: True if the port accepted a connection, False
            otherwise.
    """
    port = int(os.environ.get("LOG_API_PORT", "8090"))
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=3):
            return True
    except OSError:
        return False



if __name__ == "__main__":
    if check_port_open():
        sys.exit(0)
    sys.exit(1)
