# Backup & Restore

How to back up and restore Omeka S instances.

## How Backups Work

Each backup creates two files per instance:

| File | Contents |
|------|----------|
| `db_YYYY-MM-DD_HHMMSS.sql.gz` | MySQL database dump (gzipped) |
| `files_YYYY-MM-DD_HHMMSS.tar.gz` | Omeka S files volume (uploads, modules, themes, config) |

Backups are stored on the server at:

```
/opt/omeka-s/backups/
└── <instance-name>/
    ├── db_2026-03-12_083406.sql.gz
    └── files_2026-03-12_083406.tar.gz
```

## Enabling Backups

Backups must be enabled per instance in the inventory (either the file-based inventory under `inventories/` or a Semaphore static inventory). See [INVENTORY.md](INVENTORY.md) for full details.

```yaml
omeka_instances:
  my-instance:
    # ...
    backup_enabled: true
    backup_schedule: "0 2 * * *"    # daily at 2:00 AM
```

Both fields are required. After updating the inventory, run **Deploy All Instances** to deploy the backup script and set up the cron job.

## Running a Manual Backup

### Via Semaphore UI

Run the **Backup** task template. No extra args needed — it backs up all instances with `backup_enabled: true`.

### Via Command Line

```bash
ansible-playbook playbooks/backup.yml --limit server1
```

### Directly on the Server

```bash
sudo /usr/local/bin/omeka-backup.sh test-instance
```

## Automated Backups

When `backup_enabled: true` and `backup_schedule` are set, the deploy playbook creates a cron job that runs the backup script automatically.

Common schedules:

| Schedule | Cron expression |
|----------|----------------|
| Daily at 2 AM | `0 2 * * *` |
| Every 6 hours | `0 */6 * * *` |
| Weekly on Sunday at 3 AM | `0 3 * * 0` |
| Twice daily (noon and midnight) | `0 0,12 * * *` |

## Backup Retention

Old backups are automatically deleted after **30 days** (default). This is configurable via `backup_retention_days` in the role defaults.

A separate cleanup cron job runs daily at 4:30 AM to remove expired backups.

## Restoring from Backup

### Step 1: Find the Backup Timestamp

On the server:

```bash
sudo ls /opt/omeka-s/backups/<instance-name>/
```

This shows files like:

```
db_2026-03-12_083406.sql.gz
files_2026-03-12_083406.tar.gz
```

The timestamp is `2026-03-12_083406`.

### Step 2: Run the Restore

**Via Semaphore UI:**

Run the **Restore** task template with CLI extra args:

```
-e "instance=test-instance backup_date=2026-03-12_083406"
```

**Via command line:**

```bash
ansible-playbook playbooks/restore.yml \
  -e "instance=test-instance backup_date=2026-03-12_083406"
```

### What the Restore Does

1. Verifies both backup files exist (`db_*.sql.gz` and `files_*.tar.gz`)
2. Stops all instance containers (`docker compose down`)
3. Starts only the database container
4. Waits for MySQL to be ready
5. Restores the database from the SQL dump
6. Restores the files volume from the tar archive (replaces all contents)
7. Starts all containers
8. Waits for the instance health check to pass

## Remote Backup Sync

Backups can be synced to a remote destination using rsync or rclone. Configure in the inventory or role variables:

```yaml
backup_remote_enabled: true
backup_remote_dest: "user@backup-server:/backups/omeka"
backup_remote_method: "rsync"    # or "rclone"
```

## Listing Backups on the Server

```bash
# List all backups for an instance
sudo ls -lh /opt/omeka-s/backups/test-instance/

# Check total backup size
sudo du -sh /opt/omeka-s/backups/

# Check per-instance backup size
sudo du -sh /opt/omeka-s/backups/*/
```

## Troubleshooting

### "Backup directory not found"

The backup directory hasn't been created yet. Run **Deploy All Instances** first — the backup role creates the directories.

### "omeka-backup.sh: not found"

The backup script is deployed by the backup role during **Deploy All Instances** (or `site.yml`, which includes it). Run one of those playbooks first.

### "MYSQL_PASSWORD not found"

The instance `.env` file is missing or doesn't contain `MYSQL_PASSWORD`. Re-run **Deploy Single Instance** to regenerate it.

### Restore fails at "Verify backup files exist"

The `backup_date` doesn't match any files. Double-check the timestamp with `ls` on the server. The format is `YYYY-MM-DD_HHMMSS` (with underscore, not space).

### Database restore fails

The database container may not have started in time. Increase the retry count or try running the restore again. If the issue persists, check MySQL logs:

```bash
sudo docker logs <instance>-db-1
```
