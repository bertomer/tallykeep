# M0 frontend = static placeholder served by nginx, with /api/* proxied to the backend.
# M10 replaces this with a multi-stage build: node build → nginx serve.

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY public /usr/share/nginx/html

EXPOSE 8080

# nginx runs as root by default; we drop to a non-root user via the unprivileged image
# in v1.x once we settle on the final image.
