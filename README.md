# am-omeka-s-ansible

Ansible automation for deploying and managing multiple [Omeka S](https://omeka.org/s/) instances across Ubuntu/Debian servers using the [omeka-s-docker](https://github.com/AM-Digital-Research-Environment/omeka-s-docker) architecture.

## Architecture

```
Control machine (your PC)
  └── ansible-playbook → SSH →
        Server 1 (Ubuntu)
        ├── Caddy (shared reverse proxy, HTTPS/Let's Encrypt)
        ├── Instance A (archives.example.edu:8081) → [nginx + php + db]
        ├── Instance B (library.example.edu:8082)  → [nginx + php + db]
        └── Instance C (test.example.edu:8083)     → [nginx + php + db]

        Server 2 (Ubuntu)
        ├── Caddy
        └── Instance D (other.example.edu:8081)    → [nginx + php + db]
```

Each instance is a full clone of `omeka-s-docker` with its own `.env`, Docker volumes, and Compose project. Caddy routes domains to the correct instance port. All instance nginx ports bind to `127.0.0.1` only.

## Prerequisites

- **Control machine**: Ansible 2.15+ with Python 3.10+
- **Target servers**: Ubuntu 22.04+ or Debian 12+
- **SSH access** to target servers (key-based recommended)

## Quick Start

### 1. Install Ansible collections

```bash
ansible-galaxy collection install -r requirements.yml
```

### 2. Configure inventory

Copy and edit the example inventory:

```bash
# Edit hosts
vim inventories/production/hosts.yml

# Edit global defaults
vim inventories/production/group_vars/all/main.yml

# Define instances per server
vim inventories/production/host_vars/server1/main.yml

# Set secrets (then encrypt with ansible-vault)
vim inventories/production/host_vars/server1/vault.yml
ansible-vault encrypt inventories/production/host_vars/server1/vault.yml
```

### 3. Run full deployment

```bash
ansible-playbook playbooks/site.yml -i inventories/production --limit server1
```

## Instance Configuration

Each server's `host_vars/<server>/main.yml` contains an `omeka_instances` dict:

```yaml
omeka_instances:
  archives-main:
    domain: archives.example.edu
    omeka_version: "4.2.0"
    nginx_port: 8081
    extra_modules: [AdvancedSearch, IiifServer]
    extra_themes: [ColorMe]
    php_pm_max_children: 15
    backup_enabled: true
    backup_schedule: "0 2 * * *"

  library-digital:
    domain: digital.library.edu
    omeka_version: "4.2.0"
    nginx_port: 8082
    extra_modules: [CSVImport]
    backup_enabled: true
```

Secrets in `vault.yml` (encrypted with `ansible-vault`):

```yaml
omeka_instance_secrets:
  archives-main:
    mysql_password: "STRONG_PASSWORD"
  library-digital:
    mysql_password: "ANOTHER_PASSWORD"
```

## Playbooks

| Playbook | Description | Usage |
|----------|-------------|-------|
| `site.yml` | Full convergence (server + all instances) | `ansible-playbook playbooks/site.yml --limit server1` |
| `server-setup.yml` | Base server only (common + docker + caddy) | `ansible-playbook playbooks/server-setup.yml --limit server1` |
| `deploy-instance.yml` | Deploy single instance | `-e "instance=archives-main"` |
| `deploy-all-instances.yml` | Deploy all instances on target hosts | `--limit server1` |
| `update-omeka.yml` | Update Omeka S core | `-e "instance=archives-main target_version=4.3.0"` |
| `manage-modules.yml` | Install/update modules | `-e "instance=archives-main action=install modules=CSVImport,UniversalViewer"` |
| `manage-themes.yml` | Install/update themes | `-e "instance=archives-main action=install themes=ColorMe"` |
| `backup.yml` | Run backups for enabled instances | `--limit server1` |
| `restore.yml` | Restore from backup | `-e "instance=archives-main backup_date=2026-03-11_020000"` |
| `teardown-instance.yml` | Remove instance (requires confirmation) | `-e "instance=old-site confirm_teardown=yes"` |

## Roles

| Role | Purpose |
|------|---------|
| **common** | Base server: packages, ufw, fail2ban, SSH hardening, deploy user, unattended-upgrades |
| **docker** | Docker CE + Compose plugin from official repo, daemon.json (log rotation) |
| **caddy** | Caddy install + Caddyfile with one `reverse_proxy` block per instance domain |
| **omeka_instance** | Clone repo, template .env, docker compose up, install modules/themes, health check |
| **backup** | mysqldump + volume tar + rotation + optional remote sync + cron |
| **monitoring** | Health check script (container status + HTTP + disk) + cron + alerts |

## Target Server Layout

```
/opt/omeka-s/
├── instances/
│   ├── archives-main/          # Clone of omeka-s-docker with templated .env
│   └── library-digital/
└── backups/
    ├── archives-main/
    │   ├── db_2026-03-11_020000.sql.gz
    │   └── files_2026-03-11_020000.tar.gz
    └── library-digital/
```

## Variable Priority (lowest to highest)

1. `roles/*/defaults/main.yml` — role defaults
2. `group_vars/all/main.yml` — global defaults
3. `host_vars/<server>/main.yml` — per-server + per-instance overrides
4. `--extra-vars` — CLI overrides

## Vault Management

```bash
# Encrypt a file
ansible-vault encrypt inventories/production/host_vars/server1/vault.yml

# Edit encrypted file
ansible-vault edit inventories/production/host_vars/server1/vault.yml

# Run playbooks with vault password prompt
ansible-playbook playbooks/site.yml --ask-vault-pass

# Or use a password file
ansible-playbook playbooks/site.yml --vault-password-file .vault_pass
```

## Verification

```bash
# Syntax check
ansible-playbook playbooks/site.yml --syntax-check

# Dry run
ansible-playbook playbooks/site.yml --check --diff --limit server1

# Full run (idempotent — safe to run multiple times)
ansible-playbook playbooks/site.yml --limit server1
```
