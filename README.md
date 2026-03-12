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

- **Control machine**: Ubuntu 22.04+, Debian 12+, or WSL2 with Python 3.10+
- **Target servers**: Ubuntu 22.04+ or Debian 12+
- **SSH access** to target servers (key-based recommended)

## Quick Start

### 1. Install Ansible

**Ubuntu / Debian:**

```bash
sudo apt update && sudo apt install -y ansible
```

**pip (any platform):**

```bash
pip install ansible
```

Verify the installation:

```bash
ansible --version   # should show 2.15+
```

### 2. Install required Ansible collections

```bash
ansible-galaxy collection install -r requirements.yml
```

This installs `community.docker`, `community.general`, and `ansible.posix`.

### 3. Clone this repository

```bash
git clone https://github.com/AM-Digital-Research-Environment/am-omeka-s-ansible.git
cd am-omeka-s-ansible
```

### 4. Configure inventory

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

### 5. Run full deployment

```bash
ansible-playbook playbooks/site.yml -i inventories/production --limit server1 --ask-vault-pass
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
    extra_themes: [cozy]
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
| `manage-modules.yml` | Install/update modules | `-e "instance=archives-main modules=CSVImport,UniversalViewer"` (update: `module_action=update`) |
| `manage-themes.yml` | Install/update themes | `-e "instance=archives-main themes=cozy"` (update: `theme_action=update`) |
| `backup.yml` | Run backups for enabled instances | `--limit server1` |
| `restore.yml` | Restore from backup | `-e "instance=archives-main backup_date=2026-03-11_020000"` |
| `status.yml` | Show status of all instances | `--limit server1` |
| `teardown-instance.yml` | Remove instance (requires confirmation) | `-e "instance=old-site confirm_teardown=yes"` |

See [docs/MODULES_AND_THEMES.md](docs/MODULES_AND_THEMES.md) for the full module/theme management guide — available modules, dependencies, per-instance configuration, and usage via Semaphore or CLI.

See [docs/UPDATING_OMEKA.md](docs/UPDATING_OMEKA.md) for the Omeka S core update process — version targeting, automatic backups, rollback, and troubleshooting.

See [docs/INVENTORY.md](docs/INVENTORY.md) for inventory configuration — instance definitions, secrets, PHP-FPM tuning, backup schedules, and multi-server setup.

See [docs/BACKUP_AND_RESTORE.md](docs/BACKUP_AND_RESTORE.md) for backup and restore — automated schedules, manual backups, restoring from backup, and remote sync.

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

## Web UI (Semaphore)

A `docker-compose.semaphore.yml` is included to run [Semaphore UI](https://semaphoreui.com/) — a web interface for running playbooks, managing inventories, viewing run history, and scheduling tasks.

### Setup

```bash
# Copy and edit environment file
cp .env.example .env
vim .env   # set passwords, admin email, encryption key

# Generate an encryption key
head -c 32 /dev/urandom | base64
# Paste the output as SEMAPHORE_ACCESS_KEY_ENCRYPTION in .env

# Start Semaphore
docker compose -f docker-compose.semaphore.yml up -d
```

Open `http://<server-ip>:3000` and log in with credentials from `.env`.

### Configuring Semaphore

#### 1. Generate an SSH key for Semaphore

```bash
ssh-keygen -t ed25519 -f /tmp/semaphore_key -N "" -C semaphore
```

Add the public key to the target server's authorized_keys:

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cat /tmp/semaphore_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Ensure the target user has passwordless sudo:

```bash
sudo bash -c 'echo "<username> ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/<username>'
```

#### 2. Create a project

Click **New Project** and name it (e.g. `Omeka S Ansible`).

#### 3. Key Store

Create two keys:

| Key Name | Type | Notes |
|----------|------|-------|
| `local-access` | None | Used for public repo access |
| `ssh-key` | SSH Key | Paste the private key from `/tmp/semaphore_key` |

#### 4. Repository

| Field | Value |
|-------|-------|
| Name | `am-omeka-s-ansible` |
| URL | `https://github.com/AM-Digital-Research-Environment/am-omeka-s-ansible.git` |
| Branch | `main` |
| Access Key | `local-access` |

#### 5. Inventory

| Field | Value |
|-------|-------|
| Name | `Production` (or `Staging`) |
| Type | `Static` |
| SSH Key | `ssh-key` |

Paste a static YAML inventory:

```yaml
all:
  children:
    omeka_servers:
      hosts:
        myserver:
          ansible_host: <server-ip>
          ansible_user: <username>
          ansible_python_interpreter: /usr/bin/python3
          omeka_instances:
            my-instance:
              domain: omeka.example.edu
              omeka_version: "4.2.0"
              nginx_port: 8081
              extra_modules: []
              extra_themes: []
              backup_enabled: false
          omeka_instance_secrets:
            my-instance:
              mysql_password: "CHANGE_ME"
```

#### 6. Task Templates

Create a template for each playbook you want to run from the UI:

| Name | Playbook | Inventory | Repository |
|------|----------|-----------|------------|
| Server Setup | `playbooks/server-setup.yml` | Production | am-omeka-s-ansible |
| Deploy All Instances | `playbooks/deploy-all-instances.yml` | Production | am-omeka-s-ansible |
| Backup | `playbooks/backup.yml` | Production | am-omeka-s-ansible |

Use **CLI args** to add `--check` for dry runs or `--diff` to see changes.

## Troubleshooting / Known Issues

### Semaphore inventory: do NOT name the host `localhost`

Ansible treats `localhost` specially and forces `connection: local`, causing tasks to run inside the Semaphore container instead of on the remote server. Use any other hostname (e.g., `myserver`, `sandbox`) with `ansible_host: <ip>`.

### Shell/command tasks skip in Semaphore

Semaphore may silently enable Ansible check mode, which causes `ansible.builtin.shell` and `ansible.builtin.command` tasks to be skipped (Ansible cannot predict their outcome in check mode). Declarative modules like `copy` and `docker_compose_v2` appear to succeed in check mode but produce no actual changes ("ghost writes"). To work around this, shell tasks that must always execute use `check_mode: false`.

### Disk space

Ensure the target server has sufficient disk space before deployment. Docker images and MySQL data require significant storage. If disk fills up, MySQL and PostgreSQL (Semaphore DB) will crash. Use `sudo docker system prune -a` to reclaim space from unused images.

### MySQL initialization

On first deployment, MySQL needs time to initialize. If the DB container enters a restart loop, check logs with `sudo docker logs <container-name>` and ensure sufficient disk space and memory.

## Verification

```bash
# Syntax check
ansible-playbook playbooks/site.yml --syntax-check

# Dry run
ansible-playbook playbooks/site.yml --check --diff --limit server1

# Full run (idempotent — safe to run multiple times)
ansible-playbook playbooks/site.yml --limit server1
```
