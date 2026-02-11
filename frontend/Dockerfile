FROM node:20-bookworm-slim AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci --include=optional --no-audit --no-fund
# Workaround for npm optional-deps bug causing missing Rollup native package in containers.
RUN node -e "const cp=require('child_process');if(process.platform==='linux'&&process.arch==='x64'){let libc='gnu';try{const out=cp.execSync('ldd --version 2>&1',{stdio:['ignore','pipe','pipe']}).toString();if(/musl/i.test(out))libc='musl';}catch{}const pkg='@rollup/rollup-linux-x64-'+libc;cp.execSync('npm install --no-save --include=optional '+pkg,{stdio:'inherit'});}"

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
