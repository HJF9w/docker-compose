Set secure passwords for the variables
Ajust variables as required.

start the stack.
login with admin credentials and change password.
enable totp

then add to /config/config.php:
```
'preview_imaginary_url' => 'http://imaginary:9000',
'enabledPreviewProviders' =>      
    array (
      0 => 'OC\\Preview\\Imaginary',
      1 => 'OC\\Preview\\OpenDocument',
      2 => 'OC\\Preview\\ImaginaryPDF',
      3 => 'OC\\Preview\\MSOfficeDoc',
      4 => 'OC\\Preview\\MarkDown',
      5 => 'OC\\Preview\\MP3',
      6 => 'OC\\Preview\\MP4',
      7 => 'OC\\Preview\\AVI',
      8 => 'OC\\Preview\\Movie',
      9 => 'OC\\Preview\\MKV',
      10 => 'OC\\Preview\\XCF',
      11 => 'OC\\Preview\\JPEG',
      12 => 'OC\\Preview\\PNG',
      13 => 'OC\\Preview\\GIF',
      14 => 'OC\\Preview\\BMP',
      15 => 'OC\\Preview\\XBitmap',
      16 => 'OC\\Preview\\TXT',
    ),
'default_phone_region' => 'DE',
'maintenance_window_start' => 1,
'serverid' => 1,
```

now run:
```
docker exec -u www-data nextcloud-app-1 php occ maintenance:repair --include-expensive
docker exec -u www-data nextcloud-app-1 php occ db:add-missing-indices
```

Go to Administration settings > Basic Settings > Background jobs and ensure "Cron" is selected (it should be default).
Go to Administration settings > Basic Settings > Email server and setup and test the Mail server
Go to Administration settings > Security > Two-Factor Authentication and enable "Enforce two-factor authentication"
Go to Administration settings > Overview > Security & setup warnings and check for any problems

