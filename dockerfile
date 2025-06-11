# build stage
FROM python:3.12-slim-bookworm AS builder

# 依赖
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

# copy files
COPY pyproject.toml pdm.lock README.md /tmp/

# install dependencies and project into the local packages directory
WORKDIR /tmp
RUN mkdir __pypackages__ && pdm sync --prod -G plugins --no-editable

# run stage
FROM python:3.12-slim-bookworm

# retrieve packages from build stage
ENV PYTHONPATH=/pkgs
# copy files
WORKDIR /migangbot
COPY . /migangbot
COPY docker/build/db_config.yaml docker/build/.env /migangbot/
COPY --from=builder /tmp/__pypackages__/3.12/lib /pkgs
COPY --from=builder /tmp/__pypackages__/3.12/bin/* /bin/

# install deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    fonts-noto-cjk fonts-noto-color-emoji libzbar-dev libopencv-dev \
    build-essential libssl-dev ca-certificates libasound2 wget \
    && playwright install --with-deps chromium \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# set command/entrypoint, adapt to fit your needs
CMD aerich upgrade ; nb datastore upgrade ; nb orm upgrade ; nb run
