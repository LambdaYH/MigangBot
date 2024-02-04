# build stage
FROM python:3.12-slim-bullseye AS builder

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

# copy files
COPY pyproject.toml pdm.lock README.md /tmp/

# install dependencies and project into the local packages directory
WORKDIR /tmp
RUN mkdir __pypackages__ && pdm sync --prod -G plugins --no-editable

# run stage
FROM python:3.12-slim-bullseye

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
    && apt-get install -y --no-install-recommends fonts-noto-cjk fonts-noto-color-emoji libzbar-dev libopencv-dev \
    && playwright install --with-deps chromium \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN meme download
RUN arkkit init -SIMG

# set command/entrypoint, adapt to fit your needs
CMD nb datastore upgrade ; nb run
