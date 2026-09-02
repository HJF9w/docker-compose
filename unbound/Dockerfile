FROM alpine:3.24

# Install unbound, ca-certificates (for DoT TLS verification), tzdata, and bind-tools (for healthcheck / debugging)
RUN apk add --no-cache \
    unbound \
    ca-certificates \
    tzdata \
    bind-tools \
 && update-ca-certificates

# Create required directories and ensure proper permissions
RUN mkdir -p /etc/unbound /var/lib/unbound /var/log \
 && unbound-anchor -a /etc/unbound/root.key || true \
 && chown -R unbound:unbound /etc/unbound /var/lib/unbound

WORKDIR /etc/unbound

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose standard DNS ports
EXPOSE 53/udp 53/tcp

# Healthcheck to verify DNS resolution
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD dig @127.0.0.1 -p 53 localhost +short +tries=1 +time=2 || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["-d", "-c", "/etc/unbound/unbound.conf"]
