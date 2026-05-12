# Stage 1: build SvelteKit static output
FROM node:22-alpine AS builder

WORKDIR /app

# Copy the whole monorepo context so vite can resolve ../specs imports.
COPY package.json ./
RUN npm install

COPY . .
# specs are one level up from frontend; mounted via build context at /specs
# The vite alias @tokens resolves to ../specs/UI/mockups/_shared/tokens.css.
# Docker build context must include the specs/ directory (set at docker-compose level).
RUN npm run build

# Stage 2: serve with nginx
FROM nginx:1.27-alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8080
