# Security Hardening Guide

This document tracks security improvements for the am-omeka-s-ansible project, based on an audit against the latest Ansible documentation and best practices (March 2026).

## Current Strengths

- `.env` files templated with `mode: "0600"`
- SSH hardened: root login disabled, password authentication disabled
- UFW firewall with deny-by-default policy
- Fail2ban configured for SSH brute-force protection
- `no_log: true` on most password-handling tasks
- `set -euo pipefail` in all bash templates
- Backup volumes mounted `:ro` where appropriate
- Teardown requires explicit `confirm_teardown=yes` confirmation
- `.gitignore` excludes `.vault_pass`, `.env`, `*.secret`, `*.key`
- `validate: "visudo -cf %s"` on sudoers file prevents lockout

## Improvements

### Critical

#### 1. Encrypt vault files with Ansible Vault

**Status:** To do

Vault files contain plaintext placeholder passwords and are committed to git. Even as placeholders, this pattern risks real secrets being committed the same way.

**Files affected:**
- `inventories/production/group_vars/all/vault.yml`
- `inventories/production/host_vars/server1/vault.yml`
- `inventories/staging/host_vars/staging1/vault.yml`

**Fix:**
```bash
ansible-vault encrypt inventories/production/group_vars/all/vault.yml
ansible-vault encrypt inventories/production/host_vars/server1/vault.yml
ansible-vault encrypt inventories/staging/host_vars/staging1/vault.yml
```

**Reference:** [Ansible Vault docs](https://docs.ansible.com/ansible/latest/vault_guide/vault_encrypting_content.html)

---

#### 2. Add `| quote` filter to shell variable usage

**Status:** To do

Ansible docs require the `quote` filter when passing variables to `shell` modules to prevent command injection.

**Files affected:**
- `playbooks/update-omeka.yml` — `{{ target_version }}` passed unquoted
- `playbooks/manage-modules.yml` — `{{ _all_extra_modules | join(",") }}` passed unquoted
- `playbooks/manage-themes.yml` — same pattern as modules

**Fix example:**
```yaml
# Before
ansible.builtin.shell: |
  bash scripts/update-omeka.sh {{ target_version }}

# After
ansible.builtin.shell: |
  bash scripts/update-omeka.sh {{ target_version | quote }}
```

**Reference:** [Ansible shell module docs](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/shell_module.html)

---

### High

#### 3. Remove Semaphore default password fallbacks

**Status:** To do

`docker-compose.semaphore.yml` uses `${VAR:-fallback}` syntax with weak default passwords. If someone runs `docker compose up` without creating `.env`, the weak defaults are silently used.

**Files affected:**
- `docker-compose.semaphore.yml` — `SEMAPHORE_DB_PASS`, `SEMAPHORE_ADMIN_PASSWORD`

**Fix:**
```yaml
# Before
SEMAPHORE_DB_PASS: ${SEMAPHORE_DB_PASS:-semaphore_secret}
SEMAPHORE_ADMIN_PASSWORD: ${SEMAPHORE_ADMIN_PASSWORD:-changeme}

# After — force .env configuration, fail if missing
SEMAPHORE_DB_PASS: ${SEMAPHORE_DB_PASS}
SEMAPHORE_ADMIN_PASSWORD: ${SEMAPHORE_ADMIN_PASSWORD}
```

---

#### 4. Disable `ANSIBLE_HOST_KEY_CHECKING: "false"` in Semaphore

**Status:** To do

Disabling SSH host key checking exposes all Semaphore-managed connections to man-in-the-middle attacks.

**Files affected:**
- `docker-compose.semaphore.yml` — line 27

**Fix:** Remove the environment variable and configure `known_hosts` properly in the Semaphore UI instead.

---

#### 5. Restrict NOPASSWD sudo to specific commands

**Status:** To do

The deploy user is granted `NOPASSWD:ALL`, which is broader than necessary.

**Files affected:**
- `roles/common/tasks/users.yml` — sudoers entry

**Fix:**
```
deploy ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker compose *, /usr/bin/systemctl restart caddy, /usr/bin/systemctl reload caddy
```

> **Note:** Restricting sudo commands may require testing to ensure all playbook tasks still function correctly.

---

### Medium

#### 6. Use MySQL option file instead of `-p` on command line

**Status:** To do

Passing passwords via `-p"password"` on the command line exposes them in `/proc` and potentially in error output even with `no_log: true`.

**Files affected:**
- `playbooks/restore.yml` — database ping and restore tasks
- `roles/backup/tasks/restore.yml` — same pattern
- `roles/backup/templates/omeka-backup.sh.j2` — mysqldump command

**Fix:** Write a temporary MySQL option file:
```bash
# Write temp config
MYSQL_CNF="$(mktemp)"
chmod 600 "${MYSQL_CNF}"
printf '[client]\npassword=%s\n' "${MYSQL_PASS}" > "${MYSQL_CNF}"

# Use it
mysqldump --defaults-extra-file="${MYSQL_CNF}" -u omeka omeka

# Clean up
rm -f "${MYSQL_CNF}"
```

---

#### 7. Add backup encryption at rest

**Status:** To do

Database dumps are compressed but not encrypted. Anyone with filesystem access to the backup directory can read all data.

**Files affected:**
- `roles/backup/templates/omeka-backup.sh.j2`

**Fix:** Add GPG or age encryption after compression:
```bash
mysqldump ... | gzip | gpg --encrypt --recipient backup@example.edu \
  > "${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz.gpg"
```

---

#### 8. Document Docker group security implications

**Status:** To do

Any user in the `docker` group can mount the host filesystem and escalate to root. This is a known Docker trade-off that should be documented.

**Files affected:**
- `roles/docker/tasks/main.yml`

**Fix:** Add a comment in the task and document the risk here. Consider whether rootless Docker is feasible for this deployment.

---

### Low

#### 9. Add pre-commit hook for unencrypted vault detection

**Status:** To do

There is no automated guard against committing unencrypted secrets.

**Fix:** Add a git pre-commit hook:
```bash
#!/usr/bin/env bash
# .git/hooks/pre-commit — reject unencrypted vault files

for f in $(git diff --cached --name-only | grep 'vault.yml$'); do
  if ! head -1 "$f" | grep -q '^\$ANSIBLE_VAULT'; then
    echo "ERROR: $f is not encrypted. Run: ansible-vault encrypt $f"
    exit 1
  fi
done
```

Or use [ansible-lint](https://github.com/ansible/ansible-lint) in CI to catch this automatically.

---

#### 10. Add comments clarifying localhost-only HTTP health checks

**Status:** To do

Several health checks use `http://127.0.0.1:PORT`. This is safe (localhost only, behind Caddy HTTPS termination) but could confuse future contributors.

**Files affected:**
- `playbooks/restore.yml`
- `playbooks/manage-modules.yml`
- `playbooks/update-omeka.yml`
- `roles/omeka_instance/tasks/healthcheck.yml`

**Fix:** Add a brief comment above each health check task:
```yaml
# Health check against localhost — Caddy handles HTTPS termination for external traffic
```
