# Nextcloud Docker Stack (FPM + Nginx + Postgres + Redis)

This stack uses the `nextcloud:fpm-alpine` image for performance, coupled with a dedicated Nginx container for serving static files and handling FastCGI.

## Prerequisites

*   Docker & Docker Compose (or Portainer)
*   External Caddy reverse proxy in `system_internal` network.
*   Folder structure at `/data/nc` (or configured `BASEPATH`).

## Setup Instructions

1.  **Configure Environment:**
    Copy `.env` and update the passwords and domain.
    ```bash
    cp .env .env.local
    nano .env
    ```
    *   Set `NEXTCLOUD_HOST` to your domain.
    *   Generate strong passwords for `POSTGRES_PASSWORD`, `REDIS_HOST_PASSWORD`, and `NEXTCLOUD_ADMIN_PASSWORD`.

2.  **Permissions:**
    The FPM container runs as `www-data` (UID 82 on Alpine). Ensure the data directories exist and have the correct permissions.

    ```bash
    # Create directories
    sudo mkdir -p /data/nc/{db,html,redis}
    
    # Set ownership to www-data (uid 82) for app data
    # Postgres usually handles its own permissions (uid 70 or 999), Redis (uid 999)
    # Nextcloud needs uid 82
    sudo chown -R 82:82 /data/nc/html
    
    # Postgres (often uid 70 on alpine, verify if issues arise)
    # Redis (often uid 999)
    # Usually docker handles the volume initialization, but if bind mounting, you might need to fix ownership if they fail to start.
    ```

3.  **Start the Stack:**
    ```bash
    docker-compose up -d
    ```

4.  **Finish Installation:**
    *   Go to `https://nc.example.com`.
    *   The installation wizard might be skipped if you provided `NEXTCLOUD_ADMIN_USER` and `PASSWORD` in `.env`.
    *   If not, enter the database details:
        *   User: `nextcloud` (or value of POSTGRES_USER)
        *   Password: (value of POSTGRES_PASSWORD)
        *   Database: `nextcloud` (or value of POSTGRES_DB)
        *   Host: `db`

5.  **Post-Install Configuration:**

    **Imaginary (High Performance Image Previews):**
    Add the following to your `config/config.php` (located in `/data/nc/html/config/config.php`):
    
    ```php
    'enabledPreviewProviders' => [
      'OC\Preview\Imaginary',
      'OC\Preview\JPEG',
      'OC\Preview\GIF',
      'OC\Preview\BMP',
      'OC\Preview\XBitmap',
      'OC\Preview\MP3',
      'OC\Preview\TXT',
      'OC\Preview\MarkDown',
      'OC\Preview\OpenDocument',
      'OC\Preview\Krita',
    ],
    'preview_imaginary_url' => 'http://imaginary:9000',
    ```

    **Phone Region:**
    Add to `config.php` if not set via env:
    ```php
    'default_phone_region' => 'US',
    ```

    **APCu (Local Cache):**
    The FPM image includes APCu. To enable it fully, add to `config.php`:
    ```php
    'memcache.local' => '\OC\Memcache\APCu',
    ```

    **Background Jobs:**
    Go to Settings > Basic Settings > Background jobs and ensure "Cron" is selected (it should be default).

## Maintenance

*   **Update:** Pull new images and restart.
    ```bash
    docker-compose pull
    docker-compose up -d
    ```
*   **Backup:** Backup the `/data/nc` directory. Ideally dump the database with `pg_dump` before file backup.
*   **Troubleshooting:**
    *   **Caddy Error 502:** Ensure `nc-web-1` is the correct container name. Run `docker ps` to verify. It might be `nc_web_1` depending on your Docker Compose version.
