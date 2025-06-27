FROM ghcr.io/astral-sh/uv:alpine

WORKDIR /app

RUN apk update && apk add git

RUN uv tool install -U wialonBlock@https://github.com/o-murphy/wialonBlock.git

# Ensure installed tool in the $PATH
ENV PATH="/root/.local/bin/:$PATH"

CMD ["sh", "-c", "wialonblock \"${CONFIG_PATH:-/app/.env.toml}\" > \"${LOG_PATH:-/app/log/logfile}\" 2>&1"]
