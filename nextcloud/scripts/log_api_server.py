"""
------------------------------------------------------------------------------
Script Name:      log_api_server
Script Author:    Neal Russell
Author's Company: N/A
Script Created:   2026-Sep-07
Script Modified:  2026-Sep-07
Script Version:   1.0.0
Script Purpose:   Serve time-bounded slices of a stack's JSON-formatted
                  nginx access log over a narrow, internal-only HTTP API,
                  so external consumers (e.g. an OpenClaw reconciliation
                  job) can pull the last N hours of log lines without
                  shell/exec access to the log-owning container and
                  without transferring the full, ever-growing log file.

Script Desc:      This script will perform the following actions:
                    * Listen on an internal-only HTTP port for GET
                        requests to /logs
                    * Require a static bearer token (read from an
                        environment variable) on every request; reject
                        anything else with 401
                    * Accept 'since' (RFC3339 UTC timestamp) and 'file'
                        (a key naming one of the log files this instance
                        is allowed to serve) as query parameters
                    * Read the requested log file line by line, parse
                        each line as JSON, and compare a configurable
                        timestamp field against 'since'
                    * Return only lines at or after 'since', newline-
                        delimited JSON, so the caller can stream/parse
                        incrementally rather than loading one giant
                        response body
                    * Never expose any file, path, or capability beyond
                        what is explicitly listed in LOG_FILE_MAP below

Script Reqs:      These environment variables must be set on the
                  container running this script:
                    * LOG_API_TOKEN
                        Static bearer token this instance expects on
                        every request. Generate a unique GUID-style
                        token per stack; do not reuse across stacks.
                    * LOG_API_PORT
                        (optional) Port to listen on. Defaults to 8090.

Script Notes:     LOG_FILE_MAP below is the single point of control for
                  which files this instance is willing to serve, and
                  which JSON field in each file holds its timestamp.
                  Every file this instance can serve must be listed
                  here explicitly; there is no fallback or wildcard
                  path resolution, by design, so a misconfigured
                  request can never walk outside the intended log
                  directory.

                  This server binds to 0.0.0.0 inside its own container,
                  but is only ever reachable by other containers on the
                  same internal Docker network. It must never be added
                  to any external-facing nginx config or exposed via
                  the macvlan network's public-facing address. There is
                  no TLS termination in this script itself; TLS is
                  expected to be handled by placing this service behind
                  the stack's existing internal-only listener setup, if
                  encryption in transit is required for the internal
                  hop, or accepted as plaintext on a trusted internal-
                  only bridge network if not.

                  Timestamp comparison is a simple ISO 8601 string
                  comparison after normalizing both sides to the same
                  format, not a full datetime parse-and-diff. This is
                  intentional for speed on large files, and works
                  correctly as long as every timestamp in the source
                  log is already zero-padded, fixed-width, and in a
                  consistent format, which is true for the 'geoip_json'
                  and 'with_geo_json' nginx log formats already in use
                  across this environment.

                  This script does not handle log rotation. If the
                  active log file rotates mid-window, only the current
                  file is searched, and older matching lines in a
                  rotated file will be silently missed. Revisit this
                  once rotation is confirmed to be in play for any of
                  the stacks this script serves.

------------------------------------------------------------------------------
Execution Context: Standalone container entrypoint, run via
                   'python3 log_api_server.py'. Not a Windmill step, not
                   imported as a module elsewhere.
                   Runtime dependencies: none beyond the Python 3
                   standard library.
------------------------------------------------------------------------------
Change Log:
  1.0.0 - Initial DEV version.
------------------------------------------------------------------------------
To Do List:
  *  Confirm whether log rotation applies to any served file, and if
       so, add rotated-file lookback.
  *  Consider moving LOG_FILE_MAP to an external config file if the
       number of served files per stack grows past a small handful.
------------------------------------------------------------------------------
"""

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse



# Single point of control for every file this instance may serve.
# Each entry maps a caller-facing 'file' key to the real path on disk
# and the JSON field within each log line that holds its timestamp.
# Nothing outside this map is ever reachable through the API.
LOG_FILE_MAP = {
    "nginx_access": {
        "line_format": "json",
        "path": "/var/log/nginx/nginx_access.log",
        "timestamp_field": ("TIME", "time_local"),
        "timestamp_format": "%d/%b/%Y:%H:%M:%S %z",
    },
    "nextcloud_app": {
        "line_format": "json",
        "path": "/var/log/nextcloud.log",
        "timestamp_field": ("time",),
        "timestamp_format": None,
    },
    "mealie_app": {
        "line_format": "json",
        "path": "/var/log/mealie.log",
        "timestamp_field": ("time",),
        "timestamp_format": None,
    },
}


def load_expected_token():
    """
    Header comment: Reads the bearer token this instance requires from
    the environment at startup, and fails fast if it is missing.

    Docstring:
        Loads LOG_API_TOKEN from the environment. This is called once
        at server startup rather than per-request, since the token is
        not expected to change without a container restart.

    Returns:
        str: the expected bearer token value.

    Raises:
        RuntimeError: if LOG_API_TOKEN is unset, so the container fails
            to start rather than silently serving with no real auth.
    """
    token = os.environ.get("LOG_API_TOKEN")
    if not token:
        raise RuntimeError(
            "LOG_API_TOKEN is not set. Refusing to start without an "
            "explicit bearer token, since an unset token here would "
            "otherwise mean this endpoint accepts any/no credential."
        )
    return token



EXPECTED_TOKEN = load_expected_token()
LISTEN_PORT = int(os.environ.get("LOG_API_PORT", "8090"))



def parse_since_param(raw_value):
    """
    Header comment: Validates and normalizes the caller-supplied
    'since' query parameter into a directly comparable string.

    Docstring:
        Parses an RFC3339 UTC timestamp (e.g.
        '2026-09-06T15:00:00Z') into a datetime, then re-renders it in
        the same format used by the target log's timestamp field, so
        the two can be compared as plain strings later. Rejecting a
        malformed 'since' here, rather than downstream, keeps the
        per-line filtering loop simple and fast.

    Args:
        raw_value (str): the raw 'since' query parameter value.

    Returns:
        datetime: a timezone-aware UTC datetime.

    Raises:
        ValueError: if raw_value cannot be parsed as RFC3339 UTC.
    """
    # Accept a trailing 'Z' as UTC, since Python's fromisoformat did
    # not natively handle 'Z' prior to 3.11, and this keeps behavior
    # consistent regardless of the exact 3.x version running here.
    normalized = raw_value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)



def extract_line_timestamp(parsed_line, field_path):
    """
    Header comment: Walks a nested-field path to pull the timestamp
    value out of one parsed JSON log line.

    Docstring:
        Log lines in this environment nest their timestamp under a
        parent key (e.g. {"TIME": {"time_local": "..."}}), rather
        than at the top level. field_path is a tuple of keys to walk
        in order to reach the actual value, so this same function
        works for any log format listed in LOG_FILE_MAP without a
        format-specific branch.

    Args:
        parsed_line (dict): one JSON log line, already parsed.
        field_path (tuple): ordered keys to walk to the timestamp.

    Returns:
        str or None: the raw timestamp string, or None if any key in
            field_path is missing from this line.
    """
    current = parsed_line
    for key in field_path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current



def filter_log_lines(file_key, since_dt):
    """
    Header comment: Reads one allowed log file and yields only the
    lines at or after the requested 'since' timestamp.

    Docstring:
        Streams the target file line by line rather than loading it
        into memory at once, since these files grow unbounded over
        time. Each line is parsed as JSON; lines that fail to parse,
        or that are missing the expected timestamp field, are skipped
        rather than raising, so one malformed line cannot break the
        whole response. Timestamp parsing branches on whether the
        target file's LOG_FILE_MAP entry specifies a strptime format
        string or None; None means the field is already ISO 8601 and
        can be parsed directly with fromisoformat.

    Args:
        file_key (str): a key present in LOG_FILE_MAP.
        since_dt (datetime): timezone-aware UTC cutoff.

    Yields:
        str: raw JSON lines (already valid JSON text) that are at or
            after since_dt, in file order.

    Raises:
        KeyError: if file_key is not present in LOG_FILE_MAP. Callers
            must check this before calling, this function does not
            validate it itself.
    """
    entry = LOG_FILE_MAP[file_key]
    file_path = entry["path"]
    field_path = entry["timestamp_field"]
    timestamp_format = entry["timestamp_format"]

    with open(file_path, "r", encoding="utf-8") as log_file:
        for raw_line in log_file:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                parsed_line = json.loads(raw_line)
            except json.JSONDecodeError:
                # A malformed line should not break the whole
                # response, so skip it and move on.
                continue

            raw_timestamp = extract_line_timestamp(
                parsed_line, field_path
            )
            if raw_timestamp is None:
                continue

            try:
                if timestamp_format is None:
                    line_dt = datetime.fromisoformat(raw_timestamp)
                else:
                    line_dt = datetime.strptime(
                        raw_timestamp, timestamp_format
                    )
            except ValueError:
                continue

            if line_dt.tzinfo is None:
                line_dt = line_dt.replace(tzinfo=timezone.utc)
            line_dt = line_dt.astimezone(timezone.utc)

            if line_dt >= since_dt:
                yield raw_line



class LogApiRequestHandler(BaseHTTPRequestHandler):
    """
    Header comment: HTTP request handler implementing the single
    supported route, GET /logs, with bearer-token auth and
    query-parameter validation.

    Docstring:
        This class intentionally supports exactly one route. Any
        other path returns 404. Any request missing or presenting the
        wrong bearer token returns 401 before any file is touched.
        Any request with a 'file' value not present in LOG_FILE_MAP
        returns 400, rather than attempting to resolve an arbitrary
        path.
    """



    def _send_json_error(self, status_code, message):
        """
        Header comment: Writes a small JSON error body and the given
        HTTP status code back to the client.

        Docstring:
            Centralizes error responses so every failure path returns
            the same shape ({"error": "..."}), which keeps the caller
            side (the OpenClaw capture module) simple to write against.

        Args:
            status_code (int): HTTP status code to send.
            message (str): human-readable error message.

        Returns:
            None
        """
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)



    def _check_auth(self):
        """
        Header comment: Validates the Authorization header against the
        expected bearer token.

        Docstring:
            Looks for a header of the form 'Authorization: Bearer
            <token>' and compares it to EXPECTED_TOKEN. Any mismatch,
            including a missing header entirely, is treated the same
            way, so a caller cannot distinguish 'no token sent' from
            'wrong token sent' through timing or response differences.

        Returns:
            bool: True if the request is authorized, False otherwise.
        """
        auth_header = self.headers.get("Authorization", "")
        expected = "Bearer " + EXPECTED_TOKEN
        return auth_header == expected



    def do_GET(self):
        """
        Header comment: Entry point for every GET request; routes,
        authenticates, validates, and streams the filtered response.

        Docstring:
            Only responds to the literal path '/logs'. All validation
            (auth, then query parameters) happens before any log file
            is opened, so an unauthorized or malformed request never
            touches disk.

        Returns:
            None
        """
        parsed_url = urlparse(self.path)

        if parsed_url.path != "/logs":
            self._send_json_error(404, "Not found.")
            return

        if not self._check_auth():
            self._send_json_error(401, "Missing or invalid token.")
            return

        query = parse_qs(parsed_url.query)
        file_key = query.get("file", [None])[0]
        since_raw = query.get("since", [None])[0]

        if file_key is None or file_key not in LOG_FILE_MAP:
            self._send_json_error(
                400,
                "Missing or unrecognized 'file' parameter. Allowed "
                "values: " + ", ".join(sorted(LOG_FILE_MAP.keys())),
            )
            return

        if since_raw is None:
            self._send_json_error(
                400, "Missing required 'since' parameter."
            )
            return

        try:
            since_dt = parse_since_param(since_raw)
        except ValueError:
            self._send_json_error(
                400,
                "Could not parse 'since' as an RFC3339 UTC "
                "timestamp, e.g. 2026-09-06T15:00:00Z.",
            )
            return

        # Response is streamed as newline-delimited JSON. Headers are
        # sent before the body is generated, since the exact response
        # size is not known ahead of time for a streamed file read.
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()

        for line in filter_log_lines(file_key, since_dt):
            self.wfile.write(line.encode("utf-8"))
            self.wfile.write(b"\n")



    def log_message(self, format_string, *args):
        """
        Header comment: Overrides BaseHTTPRequestHandler's default
        stderr access logging with a minimal, consistent line.

        Docstring:
            The default implementation writes a combined-log-style
            line that includes the full request line and status,
            which is fine, but this override keeps the format
            explicit and stable in case log_api_server's own stdout
            is later fed into anything log-format-sensitive.

        Args:
            format_string (str): printf-style format string.
            *args: values to interpolate into format_string.

        Returns:
            None
        """
        print(
            "%s - - [%s] %s"
            % (
                self.address_string(),
                self.log_date_time_string(),
                format_string % args,
            )
        )



def run_server():
    """
    Header comment: Starts the threading HTTP server and blocks until
    interrupted.

    Docstring:
        Uses ThreadingHTTPServer rather than the single-threaded
        HTTPServer so one slow client streaming a large response
        cannot block a concurrent request from a second caller. This
        is expected to have very low concurrency (one internal
        consumer, a handful of requests per day), so this is a
        precaution rather than a load-driven requirement.

    Returns:
        None
    """
    server_address = ("0.0.0.0", LISTEN_PORT)
    httpd = ThreadingHTTPServer(server_address, LogApiRequestHandler)
    print(f"log_api_server listening on port {LISTEN_PORT}")
    httpd.serve_forever()



if __name__ == "__main__":
    run_server()
