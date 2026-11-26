FROM node:22-alpine AS base
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@12.3.4 --activate

COPY package.json pnpm-workspace.yaml ./
COPY packages/contracts/package.json ./packages/contracts/
COPY packages/ui/package.json ./packages/ui/
COPY packages/whiteboard-schema/package.json ./packages/whiteboard-schema/
COPY apps/web/package.json ./apps/web/

RUN pnpm install --frozen-lockfile || pnpm install

COPY packages ./packages
COPY apps/web ./apps/web

RUN pnpm --filter @go4guru/contracts build && \
    pnpm --filter @go4guru/whiteboard-schema build && \
    pnpm --filter @go4guru/ui build && \
    pnpm --filter @go4guru/web build

EXPOSE 3000
CMD ["pnpm", "--filter", "@go4guru/web", "start"]
