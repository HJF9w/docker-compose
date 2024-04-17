CREATE DATABASE IF NOT EXISTS `wordpress`;
CREATE USER 'wordpress'@'%' IDENTIFIED BY 'wordpress';
GRANT ALL PRIVILEGES ON *.* TO 'phpmyadmin'@'%';
GRANT ALL PRIVILEGES ON wordpress.* TO 'wordpress'@'%';