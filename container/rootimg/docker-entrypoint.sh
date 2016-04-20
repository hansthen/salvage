#!/bin/bash

if [[ -d /docker-entrypoint-startup.d ]]; then
    for f in /docker-entrypoint-startup.d/*; do
        echo "$0: running $f"; . "$f"
    done
fi

exec "$@"
