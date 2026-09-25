FROM python:3.12-alpine
RUN apk add --no-cache jq
COPY rootfs/app /app
COPY rootfs/run.sh /run.sh
RUN pip install --no-cache-dir aiomqtt~=2.0 && chmod +x /run.sh
WORKDIR /app
CMD ["/run.sh"]
