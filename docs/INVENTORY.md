# Inventory Configuration

How to configure the Semaphore inventory to define instances, secrets, and per-instance settings.

## Inventory Structure

The inventory is a static YAML file configured in Semaphore under **Inventory**. It defines which servers to manage and what Omeka S instances to run on each.

```yaml
all:
  children:
    omeka_servers:
      hosts:
        myserver:                                    # any name EXCEPT "localhost"
          ansible_host: 192.168.1.100                # server IP address
          ansible_user: deploy                       # SSH user
          ansible_connection: ssh
          ansible_python_interpreter: /usr/bin/python3

          omeka_instances:
            # ... instance definitions here ...

          omeka_instance_secrets:
            # ... passwords here ...
```

> **Important:** Never name the host `localhost`. Ansible forces `connection: local` for localhost, which runs tasks inside the Semaphore container instead of on the remote server.

## Instance Definition

Each instance is a key under `omeka_instances`:

```yaml
omeka_instances:
  archives-main:
    domain: archives.example.edu
    omeka_version: "4.2.0"
    nginx_port: 8081
    extra_modules: []
    extra_themes: []
    backup_enabled: true
    backup_schedule: "0 2 * * *"
    php_pm_max_children: 15
    php_pm_start_servers: 3
    php_pm_min_spare_servers: 2
    php_pm_max_spare_servers: 5
    php_pm_max_requests: 500
```

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `domain` | Public domain for Caddy reverse proxy | `archives.example.edu` |
| `omeka_version` | Omeka S version to install | `"4.2.0"` |
| `nginx_port` | Local port for instance nginx (must be unique per server) | `8081` |

### Optional Fields

| Field | Default | Description |
|-------|---------|-------------|
| `extra_modules` | `[]` | Modules to install via entrypoint (see [MODULES_AND_THEMES.md](MODULES_AND_THEMES.md)) |
| `extra_themes` | `[]` | Themes to install via entrypoint |
| `backup_enabled` | `false` | Enable automated backups |
| `backup_schedule` | - | Cron schedule for backups (required if `backup_enabled: true`) |
| `php_pm_max_children` | `5` | PHP-FPM max worker processes |
| `php_pm_start_servers` | `2` | PHP-FPM workers started on boot |
| `php_pm_min_spare_servers` | `1` | Minimum idle workers |
| `php_pm_max_spare_servers` | `3` | Maximum idle workers |
| `php_pm_max_requests` | `500` | Requests before worker respawn (prevents memory leaks) |

## Secrets

Each instance needs a MySQL password under `omeka_instance_secrets`:

```yaml
omeka_instance_secrets:
  archives-main:
    mysql_password: "STRONG_RANDOM_PASSWORD"
  library-digital:
    mysql_password: "ANOTHER_STRONG_PASSWORD"
```

> **Note:** In Semaphore's static inventory, secrets are stored in plain text. For production, consider using Ansible Vault or Semaphore's vault integration.

## Multiple Instances on One Server

Each instance must have a unique `nginx_port`. Caddy routes domains to the correct port:

```yaml
omeka_instances:
  archives-main:
    domain: archives.example.edu
    nginx_port: 8081
    omeka_version: "4.2.0"
    extra_modules:
      - AdvancedSearch
      - EasyAdmin
    extra_themes: []
    backup_enabled: true
    backup_schedule: "0 2 * * *"

  library-digital:
    domain: digital.library.edu
    nginx_port: 8082
    omeka_version: "4.2.0"
    extra_modules:
      - CSVImport
    extra_themes: []
    backup_enabled: true
    backup_schedule: "0 3 * * *"

  test-instance:
    domain: test.example.edu
    nginx_port: 8083
    omeka_version: "4.2.0"
    extra_modules: []
    extra_themes: []
    backup_enabled: false

omeka_instance_secrets:
  archives-main:
    mysql_password: "password1"
  library-digital:
    mysql_password: "password2"
  test-instance:
    mysql_password: "password3"
```

## Multiple Servers

Add more hosts under `omeka_servers`:

```yaml
all:
  children:
    omeka_servers:
      hosts:
        server1:
          ansible_host: 192.168.1.100
          ansible_user: deploy
          ansible_connection: ssh
          ansible_python_interpreter: /usr/bin/python3
          omeka_instances:
            archives-main:
              domain: archives.example.edu
              nginx_port: 8081
              # ...
          omeka_instance_secrets:
            archives-main:
              mysql_password: "password1"

        server2:
          ansible_host: 192.168.1.200
          ansible_user: deploy
          ansible_connection: ssh
          ansible_python_interpreter: /usr/bin/python3
          omeka_instances:
            other-project:
              domain: other.example.edu
              nginx_port: 8081          # can reuse ports across servers
              # ...
          omeka_instance_secrets:
            other-project:
              mysql_password: "password4"
```

## PHP-FPM Tuning Guide

Adjust PHP-FPM settings based on server resources:

| Server RAM | `max_children` | `start_servers` | `min_spare` | `max_spare` |
|-----------|----------------|-----------------|-------------|-------------|
| 1 GB | 3 | 1 | 1 | 2 |
| 2 GB | 5 | 2 | 1 | 3 |
| 4 GB | 10 | 3 | 2 | 5 |
| 8 GB+ | 15-20 | 5 | 3 | 8 |

Each PHP-FPM worker uses ~50-100 MB of RAM. Set `max_children` so that total PHP memory fits comfortably alongside MySQL and nginx.

## Backup Schedule

The `backup_schedule` field uses standard cron syntax:

```
# ┌───────── minute (0-59)
# │ ┌─────── hour (0-23)
# │ │ ┌───── day of month (1-31)
# │ │ │ ┌─── month (1-12)
# │ │ │ │ ┌─ day of week (0-6, 0=Sunday)
# │ │ │ │ │
  0 2 * * *    # Daily at 2:00 AM
  0 */6 * * *  # Every 6 hours
  0 3 * * 0    # Weekly on Sunday at 3:00 AM
```

Backups are retained for 30 days by default (configurable via `backup_retention_days`).

## Complete Example

```yaml
all:
  children:
    omeka_servers:
      hosts:
        production:
          ansible_host: 10.0.1.50
          ansible_user: bt310355
          ansible_connection: ssh
          ansible_python_interpreter: /usr/bin/python3

          omeka_instances:
            archives-main:
              domain: archives.example.edu
              omeka_version: "4.2.0"
              nginx_port: 8081
              extra_modules:
                - AdvancedSearch
                - EasyAdmin
                - CSSEditor
              extra_themes: []
              backup_enabled: true
              backup_schedule: "0 2 * * *"
              php_pm_max_children: 10
              php_pm_start_servers: 3
              php_pm_min_spare_servers: 2
              php_pm_max_spare_servers: 5

            test-instance:
              domain: test.example.edu
              omeka_version: "4.2.0"
              nginx_port: 8082
              extra_modules: []
              extra_themes: []
              backup_enabled: false

          omeka_instance_secrets:
            archives-main:
              mysql_password: "use-a-strong-random-password"
            test-instance:
              mysql_password: "test-only-password"
```
