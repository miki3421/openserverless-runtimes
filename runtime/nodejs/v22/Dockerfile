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

FROM node:22.23.4-bookworm@sha256:e273cf2a19c7334c03f52e2ca933ecdfc3fbfaad49db7b8bc8c3edd9ac34e9c7 AS openexr-security
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake debhelper dh-buildinfo dpkg-dev patch && rm -rf /var/lib/apt/lists/*
COPY security/ /security/
RUN sh /security/build-openexr.sh

FROM node:22.23.4-bookworm@sha256:e273cf2a19c7334c03f52e2ca933ecdfc3fbfaad49db7b8bc8c3edd9ac34e9c7
# Preserve the compilation compatibility marker for existing v22 action archives.
ENV OW_EXECUTION_ENV=apacheopenserverless/nodejs-22.23.2
COPY --from=builder /go/bin/proxy /bin/proxy

ENV OW_COMPILER=/bin/compile
ENV OW_LOG_INIT_ERROR=1
ENV OW_WAIT_FOR_ACK=1

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    imagemagick \
    graphicsmagick \
    unzip \
    && rm -rf /var/lib/apt/lists/*

COPY --from=openexr-security /out/ /tmp/openexr-security/
RUN test "$(dpkg-query -W -f='${Version}' libopenexr-3-1-30)" = '3.1.5-5' \
    && test "$(dpkg-query -W -f='${Version}' libopenexr-dev)" = '3.1.5-5' \
    && cd /tmp/openexr-security && sha256sum -c SHA256SUMS \
    && dpkg -i ./*.deb \
    && mkdir -p /usr/share/ops-security/openexr \
    && cp SOURCE SHA256SUMS openexr-idmanifest.patch openexr-LICENSE.md changelog /usr/share/ops-security/openexr/ \
    && rm -rf /tmp/openexr-security

RUN npm install --global npm@11.21.2 && npm cache clean --force

COPY package.json package-lock.json /
COPY bin/prepare-dependencies.cjs /tmp/ops-prepare-dependencies.cjs
RUN npm config set fetch-retry-maxtimeout 60000 -g
RUN cd / && npm ci --omit=dev \
    && node /tmp/ops-prepare-dependencies.cjs / \
    && rm /tmp/ops-prepare-dependencies.cjs \
    && npm cache clean --force

COPY node-security/ /usr/share/ops-security/node-dependencies/
RUN python3 /usr/share/ops-security/node-dependencies/apply.py

RUN mkdir -p /app/action ;\
  chmod -R 0775 /app ;\
  chown -R nobody:root /app

ENV HOME=/app
WORKDIR /app
COPY bin/compile /bin/compile
COPY lib/launcher.js /lib/launcher.js

EXPOSE 8080
USER nobody

# Apache release metadata (see DISCLAIMER, LICENSE, NOTICE)
COPY DISCLAIMER LICENSE NOTICE /

ENTRYPOINT ["/bin/proxy"]
