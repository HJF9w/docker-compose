#!/bin/sh
set -e

# Update / initialize DNSSEC root trust anchor if needed
if [ ! -s /etc/unbound/root.key ]; then
    unbound-anchor -a /etc/unbound/root.key || true
fi

# Ensure appropriate ownership for unbound runtime files
chown -R unbound:unbound /etc/unbound /var/lib/unbound 2>/dev/null || true

# Validate configuration file syntax before launching
unbound-checkconf /etc/unbound/unbound.conf

# Execute unbound in foreground
exec unbound "$@"
