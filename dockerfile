# build stage
FROM python:3.11-slim AS builder

# install PDM
RUN pip install pdm

# copy files
COPY . /migangbot

WORKDIR /migangbot
RUN pdm run install
# install deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk fonts-noto-color-emoji libzbar-dev libopencv-dev
RUN pdm run playwright install --with-deps chromium
RUN pdm run meme download --url https://raw.githubusercontent.com/MeetWq/meme-generator/
RUN pdm run arkkit init -SIMG

COPY docker/build/db_config.yaml db_config.yaml
COPY docker/build/.env .env

# set command/entrypoint, adapt to fit your needs
CMD ["pdm", "run", "all"]
