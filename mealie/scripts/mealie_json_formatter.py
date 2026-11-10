import json
import logging
import re

# Attributes that exist on every LogRecord by default — anything NOT in this
# set was attached via logging.info(..., extra={...}), and gets automatically
# included in the JSON output.
_STANDARD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName", "message",
}

# uvicorn access log message format:
#   127.0.0.1:49080 - "GET /api/app/about HTTP/1.1" 200
_ACCESS_LOG_RE = re.compile(
    r'^(?P<client_ip>[^\s:]+):(?P<client_port>\d+)\s+-\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]+)"\s+'
    r'(?P<status>\d+)$'
)


class JsonFormatter(logging.Formatter):
    """Formats log records as a single line of JSON, auto-including any
    extra fields attached to the record, and parsing uvicorn's access log
    line into individual fields."""

    def __init__(self, datefmt: str = "%Y-%m-%dT%H:%M:%S"):
        super().__init__(datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()

        payload = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.threadName,
            "message": message,
        }

        # Auto-capture any non-standard attributes attached to this record
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in payload:
                payload[key] = value

        # uvicorn access logs pack everything into one message string —
        # break it into individually filterable fields.
        if record.name == "uvicorn.access":
            match = _ACCESS_LOG_RE.match(message)
            if match:
                fields = match.groupdict()
                payload["remote_addr"] = fields["client_ip"]
                payload["remote_port"] = int(fields["client_port"])
                payload["http_method"] = fields["method"]
                payload["http_path"] = fields["path"]
                payload["http_protocol"] = fields["protocol"]
                payload["http_status"] = int(fields["status"])

                # Split query string out of the path for easier filtering
                if "?" in fields["path"]:
                    route, query = fields["path"].split("?", 1)
                    payload["http_route"] = route
                    payload["http_query"] = query
                else:
                    payload["http_route"] = fields["path"]

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)
