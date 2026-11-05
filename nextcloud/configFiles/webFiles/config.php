<?php

/*
 * WARNING
 *
 * This file gets modified by automatic processes and all lines that are not
 * active code (ie. comments) are lost during that process.
 *
 * If you want to document things with comments or use constants add your settings
 * in a '<NAME>.config.php' file which will be included and rendered into this file.
 *
 * Example:
 *   <?php
 *   $CONFIG = [];
 *
 * See also: https://docs.nextcloud.com/server/latest/admin_manual/configuration_server/config_sample_php_parameters.html#multiple-merged-configuration-files
 */
$CONFIG = array (
  'csrf.optout' => 
  array (
    0 => '/Nextcloud-android/',
    1 => '/Nextcloud-iOS/',
  ),
  'htaccess.RewriteBase' => '/',
  'memcache.local' => '\\OC\\Memcache\\APCu',
  'apps_paths' => 
  array (
    0 => 
    array (
      'path' => '/var/www/html/apps',
      'url' => '/apps',
      'writable' => false,
    ),
    1 => 
    array (
      'path' => '/var/www/html/custom_apps',
      'url' => '/custom_apps',
      'writable' => true,
    ),
  ),
  'memcache.distributed' => '\\OC\\Memcache\\Redis',
  'memcache.locking' => '\\OC\\Memcache\\Redis',
  'redis' => 
  array (
    'host' => 'nextcloud_redis',
    'password' => 'change-me',
    'port' => 6379,
  ),
  'trusted_proxies' => 
  array (
    0 => '192.0.2.8',
    1 => '192.0.2.9',
    2 => '192.0.2.20',
  ),
  'upgrade.disable-web' => true,
  'passwordsalt' => 'change-me',
  'secret' => 'change-me',
  'trusted_domains' => 
  array (
    0 => 'localhost',
    1 => 'example.com',
    2 => 'example.com',
    3 => 'www.example.com',
    4 => 'drive.example.com',
    5 => 'd.example.com',
    6 => 'example.org',
    7 => 'nextcloud_app',
    8 => '192.0.2.20',
  ),
  'datadirectory' => '/var/www/data',
  'dbtype' => 'pgsql',
  'version' => '35.0.2.2',
  'overwrite.cli.url' => 'https://example.com/',
  'dbname' => 'nextcloud',
  'dbhost' => 'nextcloud_db',
  'dbport' => '',
  'dbtableprefix' => 'oc_',
  'dbuser' => 'change-me',
  'dbpassword' => 'change-me',
  'installed' => true,
  'instanceid' => 'change-me',
  'ldapProviderFactory' => 'OCA\\User_LDAP\\LDAPProviderFactory',
  'loglevel' => 2,
  'maintenance' => false,
  'mail_domain' => 'gmail.com',
  'mail_from_address' => 'change-me',
  'mail_imap_timeout' => 120,
  'mail_imap_log' => true,
  'mail_sendmailmode' => 'smtp',
  'mail_smtpauth' => 1,
  'mail_smtphost' => 'smtp.gmail.com',
  'mail_smtpmode' => 'smtp',
  'mail_smtpname' => 'change-me',
  'mail_smtpport' => '465',
  'mail_smtpsecure' => 'ssl',
  'mail_smtppassword' => 'change-me',
  'default_phone_region' => 'US',
  'maintenance_window_start' => 1,
  'serverid' => '1',
  'allow_local_remote_servers' => 
  array (
    0 => '192.0.2.101',
    1 => 'wind.example.com',
  ),
);
