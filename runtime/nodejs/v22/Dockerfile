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

FROM node:22.23.4-bookworm@sha256:e273cf2a19c7334c03f52e2ca933ecdfc3fbfaad49db7b8bc8c3edd9ac34e9c7 AS native-security
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake debhelper dh-sequence-gnome dh-sequence-python3 meson ninja-build gettext \
    docbook-xml docbook-xsl libdbus-1-dev libelf-dev libffi-dev libmount-dev \
    libpcre2-dev libselinux1-dev python3-distutils xsltproc libxml2-utils \
    dbus-daemon shared-mime-info autoconf automake libtool chrpath lynx \
    libreadline-dev libyuv-dev pkgconf tcl8.6-dev yasm \
    && rm -rf /var/lib/apt/lists/*
COPY security/build-glib.sh security/glib-introspection.patch /security/
RUN sh /security/build-glib.sh \
    && meson test -C /build/glib/source/debian/build/deb --no-rebuild \
       --print-errorlogs gdbus-introspection > /out/glib/gdbus-test.log
COPY security/build-sqlite.sh security/sqlite-distinct-order.patch /security/
RUN sh /security/build-sqlite.sh \
    && echo '4dd1a1468693239801037c1d0decd9eaac0db83f9225997404afb590b5b79722  /build/sqlite/source/src/where.c' | sha256sum -c
COPY security/build-aom.sh security/aom-bookworm-abi.patch /security/
RUN sh /security/build-aom.sh
COPY security/build-libxml2.sh security/libxml2-cve-2026-6653.patch /security/
RUN sh /security/build-libxml2.sh

# Export the independently verified Bookworm package backports as a minimal,
# digest-pinned carrier for the other ADV Python-based images.  The carrier is
# built explicitly with --target and is never selected as the Node runtime.
FROM scratch AS bookworm-native-security-packages
COPY --from=native-security /out/sqlite/ /out/sqlite/
COPY --from=native-security /out/libxml2/ /out/libxml2/

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

# The managed Node runtime has no supported SSH client contract.  Remove the
# inherited client instead of carrying a remotely triggerable protocol parser.
RUN installed_version="$(dpkg-query -W -f='${Version}' openssh-client)" \
    && test "$installed_version" = '1:9.2p1-2+deb12u10' \
    && apt-get purge -y openssh-client \
    && test "$(dpkg-query -W -f='${db:Status-Status}' openssh-client 2>/dev/null || true)" != installed \
    && ! command -v ssh >/dev/null 2>&1 \
    && ! command -v scp >/dev/null 2>&1 \
    && ! command -v sftp >/dev/null 2>&1 \
    && mkdir -p /usr/share/ops-security/openssh-removal \
    && printf '%s\n' \
       "Removed openssh-client ${installed_version}." \
       'CVE-2026-60002: the default managed action runtime does not support an inherited SSH client.' \
       > /usr/share/ops-security/openssh-removal/SOURCE

COPY --from=openexr-security /out/ /tmp/openexr-security/
RUN test "$(dpkg-query -W -f='${Version}' libopenexr-3-1-30)" = '3.1.5-5' \
    && test "$(dpkg-query -W -f='${Version}' libopenexr-dev)" = '3.1.5-5' \
    && cd /tmp/openexr-security && sha256sum -c SHA256SUMS \
    && dpkg -i ./*.deb \
    && mkdir -p /usr/share/ops-security/openexr \
    && cp SOURCE SHA256SUMS openexr-idmanifest.patch openexr-deep.patch openexr-LICENSE.md changelog /usr/share/ops-security/openexr/ \
    && rm -rf /tmp/openexr-security

COPY --from=native-security /out/glib/ /tmp/glib-security/
COPY --from=native-security /out/sqlite/ /tmp/sqlite-security/
COPY --from=native-security /out/aom/ /tmp/aom-security/
COPY --from=native-security /out/libxml2/ /tmp/libxml2-security/
RUN test "$(dpkg-query -W -f='${Version}' libglib2.0-0)" = '2.74.6-2+deb12u9' \
    && cd /tmp/glib-security && sha256sum -c SHA256SUMS && dpkg -i ./*.deb \
    && mkdir -p /usr/share/ops-security/glib \
    && cp SOURCE SHA256SUMS patched-source.sha256 glib-introspection.patch copyright changelog gdbus-test.log ./*.dsc /usr/share/ops-security/glib/ \
    && test "$(dpkg-query -W -f='${Version}' libsqlite3-0)" = '3.40.1-2+deb12u2' \
    && cd /tmp/sqlite-security && sha256sum -c SHA256SUMS && dpkg -i ./*.deb \
    && mkdir -p /usr/share/ops-security/sqlite \
    && cp SOURCE SHA256SUMS patched-source.sha256 sqlite-distinct-order.patch copyright changelog distinct-test.log ./*.dsc /usr/share/ops-security/sqlite/ \
    && rm -rf /tmp/glib-security /tmp/sqlite-security

RUN test "$(dpkg-query -W -f='${Version}' libaom3)" = '3.6.0-1+deb12u3' \
    && cd /tmp/aom-security && sha256sum -c SHA256SUMS && dpkg -i ./*.deb \
    && mkdir -p /usr/share/ops-security/aom \
    && cp SOURCE SHA256SUMS bookworm-source.sha256 resize-regression.log aom-bookworm-abi.patch copyright changelog ./*.dsc /usr/share/ops-security/aom/ \
    && rm -rf /tmp/aom-security

RUN test "$(dpkg-query -W -f='${Version}' libxml2)" = '2.9.14+dfsg-1.3~deb12u6' \
    && test "$(dpkg-query -W -f='${Version}' libxml2-dev)" = '2.9.14+dfsg-1.3~deb12u6' \
    && cd /tmp/libxml2-security && sha256sum -c SHA256SUMS && dpkg -i ./*.deb \
    && mkdir -p /usr/share/ops-security/libxml2 \
    && cp SOURCE SHA256SUMS patched-source.sha256 libxml2-cve-2026-6653.patch copyright changelog test-build.log runtest.log remaining-tests.log test-summary.txt ./*.dsc /usr/share/ops-security/libxml2/ \
    && rm -rf /tmp/libxml2-security

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

COPY npm-security/ /usr/share/ops-security/npm-dependencies/
RUN python3 /usr/share/ops-security/npm-dependencies/apply.py

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
