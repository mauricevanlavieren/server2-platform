# Isolated candidate: official Docker Library Python, linux/amd64 digest pinned.
FROM docker.io/library/python:3.13.16-alpine3.23@sha256:a237388397d835ba00539990f15487187eacf17d160c21aaa9e951818344f0dd
# Native stable packages only: security fix plus existing IPv6 guard dependency.
# apk verifies package signatures with the trusted keys retained from the official base.
COPY vendor/zlib.apk vendor/libseccomp.apk /tmp/
RUN echo "ee62e1864c235901e2aa4d1868c7ae8f7cc5d0740a98c48a2525332eb4bfda73  /tmp/zlib.apk" | sha256sum -c - \
    && echo "40132d53050deddad00d74ec304ae766b75a1df967ed10369f5e6736b8f4ac74  /tmp/libseccomp.apk" | sha256sum -c - \
    && apk add --no-network --no-cache /tmp/zlib.apk /tmp/libseccomp.apk \
    && apk info --exists 'zlib=1.3.2-r1' 'libseccomp=2.6.1-r0' \
    && rm /tmp/zlib.apk /tmp/libseccomp.apk
# Runtime is stdlib-only; keep the OS package database for complete scanning.
RUN rm -rf /usr/local/lib/python3.13/site-packages/pip /usr/local/lib/python3.13/site-packages/pip-*.dist-info /usr/local/lib/python3.13/ensurepip \
    && rm -f /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.13 \
    && rm -f /bin/mount /bin/umount /bin/su /usr/bin/mount /usr/bin/umount /usr/bin/nsenter /usr/bin/unshare /usr/bin/setpriv /usr/bin/su /usr/sbin/runuser /usr/sbin/chroot \
    && find /usr -xdev -type f -perm /6000 -exec chmod a-s {} + \
    && find /bin /sbin -xdev -type f -perm /6000 -exec chmod a-s {} +
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
