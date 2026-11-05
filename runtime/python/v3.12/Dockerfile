#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

ARG COMMON=missing:missing
FROM ${COMMON} AS builder

FROM python:3.12.16-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df
# Preserve the marker accepted by existing compiled Python 3.12 archives.
ENV OW_EXECUTION_ENV=apacheopenserverless/runtime-python-v3.12.14
COPY --from=builder /go/bin/proxy /bin/proxy

# install zip
RUN apt-get update && apt-get upgrade -y && apt-get install -y python3-lxml zip \
    && rm -rf /var/lib/apt/lists/*

# Install common modules for python
COPY requirements.txt requirements.txt

RUN python -m pip install --no-cache-dir pip==26.3 && \
    python -m pip install --no-cache-dir -r requirements.txt && \
    python -m pip check

RUN mkdir -p /action
WORKDIR /

ADD bin/compile /bin/compile
ADD lib/launcher.py /lib/launcher.py

# log initialization errors
ENV OW_LOG_INIT_ERROR=1
# the launcher must wait for an ack
ENV OW_WAIT_FOR_ACK=1
# using the runtime name to identify the execution environment
# compiler script
ENV OW_COMPILER=/bin/compile
# home directory
ENV HOME=/tmp

WORKDIR /action
RUN chown nobody:root /action ; chmod 0775 /action
USER nobody
# Apache release metadata (see DISCLAIMER, LICENSE, NOTICE)
COPY DISCLAIMER LICENSE NOTICE /

ENTRYPOINT ["/bin/proxy"]
