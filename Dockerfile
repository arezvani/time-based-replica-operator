ARG PYTHON_BASE_IMAGE=$PYTHON_BASE_IMAGE
ARG PYTHON_VERSION=$PYTHON_VERSION

FROM $PYTHON_BASE_IMAGE:$PYTHON_VERSION-slim as builder

ARG OS_PACKAGES=$OS_PACKAGES
ARG DOCKERFILE_PATH=$DOCKERFILE_PATH

ENV PIP_DEFAULT_TIMEOUT=1000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DOCKERFILE_PATH=$DOCKERFILE_PATH \
    OS_PACKAGES=$OS_PACKAGES

RUN apt-get update && \
    apt-get install -y --no-install-recommends `echo $OS_PACKAGES | sed 's+,+ +g'`

RUN groupadd -g 1001 abriment && \
    useradd -r -u 1001 -g abriment abriment

RUN mkdir /operator && chown abriment:abriment /operator

COPY --chown=abriment:abriment . /operator

WORKDIR /operator

RUN pip install  --no-cache -r $DOCKERFILE_PATH/requirements.txt

USER 1001

ENTRYPOINT kopf run src/tbr.py --liveness=http://0.0.0.0:8080/healthz
