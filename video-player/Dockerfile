# Use Node LTS
FROM node:26-alpine@sha256:6f08a523443ddedf52941874c203475b0ad503e859ad70cb26ab8be9a517dbd5

# Install ffmpeg for thumbnail generation (optional)
RUN apk add --no-cache ffmpeg

WORKDIR /app

# copy package files first for caching
COPY package.json package-lock.json* ./
RUN npm install --production

# copy app
COPY . .

# create data and thumbs dirs with permissive perms
RUN mkdir -p /app/data /app/thumbs && chmod -R 755 /app/data /app/thumbs

EXPOSE 3000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["npm", "start"]

