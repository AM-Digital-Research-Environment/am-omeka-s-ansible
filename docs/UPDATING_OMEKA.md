# Updating Omeka S

How to update the Omeka S core version for a specific instance.

## How It Works

The update process runs inside the PHP container via `scripts/update-omeka.sh` (from the [omeka-s-docker](https://github.com/AM-Digital-Research-Environment/omeka-s-docker) repo). The key steps are:

1. Creates a timestamped backup of `/config`, `/modules`, and `/themes`
2. Downloads the target Omeka S release from GitHub
3. Removes old core files (preserving `/files`, `/modules`, `/themes`, `/config`, `/sideload`)
4. Copies new release files into the container
5. Restores `local.config.php`, `database.ini`, modules, and themes from backup
6. Sets ownership and permissions
7. Clears OPcache and Omeka S cache
8. Restarts the PHP container

After the script completes, Ansible recreates all containers and runs a health check.

## Usage

### Via Semaphore UI

Run the **Update Omeka S** task template with CLI extra args:

```
-e "instance=test-instance target_version=4.3.0"
```

To update to the latest release:

```
-e "instance=test-instance target_version=latest"
```

### Via Command Line

```bash
ansible-playbook playbooks/update-omeka.yml \
  -e "instance=test-instance target_version=4.3.0"
```

## Version Targeting

| Value | Behavior |
|-------|----------|
| `4.3.0` | Update to exact version 4.3.0 |
| `v4.3.0` | Same (the `v` prefix is stripped automatically) |
| `latest` | Fetches the latest release tag from GitHub |

The script verifies the release exists on GitHub before proceeding. If the version is not found, the update aborts with no changes made.

## What Gets Preserved

| Directory | Behavior |
|-----------|----------|
| `/files` | Preserved in-place (never touched) |
| `/modules` | Backed up, then restored after core update |
| `/themes` | Backed up, then restored after core update |
| `/config` | Backed up; `local.config.php` and `database.ini` restored |
| `/sideload` | Preserved in-place |

## Backups

Every update creates a timestamped backup inside the container at:

```
/var/www/html/omeka-backups/backup_YYYYMMDD_HHMMSS/
├── config/
│   ├── local.config.php
│   └── database.ini
├── modules/
│   └── ... (all installed modules)
└── themes/
    └── ... (all installed themes)
```

These backups are stored in the Docker volume and persist across container restarts.

## Rollback

If something goes wrong after an update, roll back manually on the server:

```bash
cd /opt/omeka-s/instances/<instance-name>

# Find the backup timestamp
sudo docker compose exec php ls /var/www/html/omeka-backups/

# Restore from backup (replace TIMESTAMP with actual value)
sudo docker compose exec php cp /var/www/html/omeka-backups/backup_TIMESTAMP/config/local.config.php /var/www/html/config/
sudo docker compose exec php cp /var/www/html/omeka-backups/backup_TIMESTAMP/config/database.ini /var/www/html/config/
sudo docker compose exec php cp -r /var/www/html/omeka-backups/backup_TIMESTAMP/modules/* /var/www/html/modules/
sudo docker compose exec php cp -r /var/www/html/omeka-backups/backup_TIMESTAMP/themes/* /var/www/html/themes/

# Restart to apply
sudo docker compose restart php
```

## Post-Update Checklist

After a successful update:

1. Visit the Omeka S site in a browser
2. Run any database migrations if prompted
3. Check that all modules are working
4. Verify themes are displaying correctly
5. Test file/media uploads and access

## Updating Multiple Instances

Run the playbook once per instance. There is no batch update — this is intentional to allow verification between updates:

```bash
ansible-playbook playbooks/update-omeka.yml -e "instance=archives-main target_version=4.3.0"
# verify archives-main is working...

ansible-playbook playbooks/update-omeka.yml -e "instance=library-digital target_version=4.3.0"
# verify library-digital is working...
```

## Troubleshooting

### "Release not found" error

The version doesn't exist on GitHub. Check available versions at:
https://github.com/omeka/omeka-s/releases

### "PHP container is not running" error

The instance must be running before updating. Start it first:

```bash
cd /opt/omeka-s/instances/<instance-name>
sudo docker compose up -d
```

### Update succeeds but site shows errors

This usually means a module is incompatible with the new Omeka S version. Check the PHP container logs:

```bash
sudo docker logs <instance>-php-1 2>&1 | tail -50
```

If needed, disable the problematic module by removing its directory and restarting:

```bash
sudo docker compose exec php rm -rf /var/www/html/modules/<ModuleName>
sudo docker compose restart php
```
