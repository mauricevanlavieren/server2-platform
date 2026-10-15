# Official Docker Library Python, verified linux/amd64 manifest.
FROM docker.io/library/python:3.13.16-slim-trixie@sha256:8fb4cfa1a2616d7b8e0c2175cc6ad68f5729c34ea8488c0b360d2934b7be9024
# Official Debian trixie-security update, package version and SHA256 locked.
COPY vendor/liblzma.deb /tmp/liblzma.deb
RUN echo "b38acab30f295bf1066a6632e31cbd0a1980f2924b38040cda131d5dea5384ec  /tmp/liblzma.deb" | sha256sum -c - \
    && dpkg -i /tmp/liblzma.deb \
    && test "$(dpkg-query -W -f='${Version}' liblzma5)" = '5.8.1-1+deb13u2' \
    && rm /tmp/liblzma.deb \
    && rm -f /usr/bin/mount /usr/bin/umount /usr/bin/nsenter /usr/bin/unshare /usr/bin/setpriv /usr/bin/su /usr/sbin/runuser /usr/sbin/chroot \
    && find /usr -xdev -type f -perm /6000 -exec chmod a-s {} +
# Runtime uses only stdlib; remove unused installer, vendored code and reinstall wheel.
RUN test -d /usr/local/lib/python3.13/site-packages/pip && rm -rf /usr/local/lib/python3.13/site-packages/pip /usr/local/lib/python3.13/site-packages/pip-26.2.1.dist-info /usr/local/lib/python3.13/ensurepip /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.13
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    POSTKAMER_BIND=0.0.0.0 POSTKAMER_PORT=8765 \
    POSTKAMER_DB=/data/demo.sqlite \
    POSTKAMER_ALLOWED_HOSTS=127.0.0.1:8765,localhost:8765
WORKDIR /app
RUN mkdir -p /data && chown 10001:10001 /data && chmod 0700 /data
COPY maildemo/ /app/maildemo/
COPY data/messages.json /app/data/messages.json
USER 10001:10001
EXPOSE 8765
HEALTHCHECK --interval=15s --timeout=4s --start-period=15s --retries=3 CMD ["python", "-B", "-m", "maildemo.healthcheck"]
CMD ["python", "-B", "-m", "maildemo"]
