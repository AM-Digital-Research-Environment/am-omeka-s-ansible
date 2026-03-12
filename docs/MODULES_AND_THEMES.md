# Module & Theme Management

How to install, update, and manage Omeka S modules and themes per instance using the Ansible playbooks or Semaphore UI.

## How It Works

1. The playbook writes an `EXTRA_MODULES` (or `EXTRA_THEMES`) line to the instance's `.env` file
2. Containers are recreated with `docker compose down && up`
3. The container entrypoint reads the env var and downloads/installs each module from GitHub
4. Dependencies are resolved automatically (e.g., `EasyAdmin` pulls in `Common` and `Cron`)

Modules that already exist on disk are skipped. The entrypoint only downloads missing ones.

## Installing Modules

### Via Semaphore UI

Run the **Install Modules** task template with these **CLI extra args**:

```
-e "instance=test-instance modules=CSSEditor"
```

Multiple modules:

```
-e "instance=test-instance modules=EasyAdmin,CSSEditor,AdvancedSearch"
```

### Via Command Line

```bash
ansible-playbook playbooks/manage-modules.yml \
  -e "instance=test-instance modules=EasyAdmin,CSSEditor"
```

## Updating Modules

To force re-download of an already-installed module (removes the module directory first):

**Semaphore:**

```
-e "instance=test-instance modules=CSSEditor module_action=update"
```

**CLI:**

```bash
ansible-playbook playbooks/manage-modules.yml \
  -e "instance=test-instance modules=CSSEditor module_action=update"
```

## Installing Themes

Same pattern, using the **Install Themes** task template (or `manage-themes.yml`):

```
-e "instance=test-instance themes=cozy"
```

Update:

```
-e "instance=test-instance themes=cozy theme_action=update"
```

## Available Modules (Short Names)

The container entrypoint has a built-in registry of known modules. You can use just the module name (no repo/branch needed):

### Official Omeka S Modules

| Module | Repository |
|--------|------------|
| CSSEditor | omeka-s-modules/CSSEditor |
| Collecting | omeka-s-modules/Collecting |
| CustomVocab | omeka-s-modules/CustomVocab |
| Datavis | omeka-s-modules/Datavis |
| Exports | omeka-s-modules/Exports |
| Hierarchy | omeka-s-modules/Hierarchy |
| InverseProperties | omeka-s-modules/InverseProperties |
| OutputFormats | omeka-s-modules/OutputFormats |
| ResourceMeta | omeka-s-modules/ResourceMeta |
| ValueSuggest | omeka-s-modules/ValueSuggest |

### Daniel-KM Modules

| Module | Repository | Dependencies |
|--------|------------|--------------|
| AdvancedSearch | Daniel-KM/...AdvancedSearch | Common |
| AnalyticsSnippet | Daniel-KM/...AnalyticsSnippet | - |
| BulkEdit | Daniel-KM/...BulkEdit | Common |
| BulkExport | Daniel-KM/...BulkExport | Common |
| Common | Daniel-KM/...Common | - |
| Cron | Daniel-KM/...Cron | - |
| EasyAdmin | Daniel-KM/...EasyAdmin | Common, Cron |
| IiifServer | Daniel-KM/...IiifServer | Common |
| ImageServer | Daniel-KM/...ImageServer | Common |
| Log | Daniel-KM/...Log | Common |
| OaiPmhRepository | Daniel-KM/...OaiPmhRepository | Common |
| Reference | Daniel-KM/...Reference | Common |
| SearchSolr | Daniel-KM/...SearchSolr | Common, AdvancedSearch |
| UniversalViewer | Daniel-KM/...UniversalViewer | Common |

### Other Modules

| Module | Repository |
|--------|------------|
| RightsStatements | zerocrates/RightsStatements |
| Sitemaps | ManOnDaMoon/omeka-s-module-Sitemaps |

### Default Modules (Pre-installed)

These are installed automatically on every instance by the entrypoint:

- ActivityLog
- CSVImport
- DataCleaning
- DspaceConnector
- FacetedBrowse
- FileSideload
- IframeEmbed
- ItemCarouselBlock
- Mapping
- NumericDataTypes

### Default Themes (Pre-installed)

- default
- Freedom
- Lively

### Available Extra Themes

All themes from the [omeka-s-themes](https://github.com/omeka-s-themes) GitHub organization can be installed by name:

| Theme | Description |
|-------|-------------|
| cozy | Off-canvas navigation menu |
| foundation | Based on ZURB Foundation |
| papers | Based on Papers of the War Department |
| thedaily | Bold sans-serifs with bright color accents |

## Custom Modules (Not in Registry)

For modules not in the known registry, use the full format `ModuleName:org/repo:branch`:

```
-e "instance=test-instance modules=MyModule:github-user/my-module-repo:main"
```

## Dependencies

Dependencies are resolved automatically by the entrypoint. For example, installing `EasyAdmin` will also install `Common` and `Cron` if they are not already present.

The full dependency map:

| Module | Requires |
|--------|----------|
| AdvancedSearch | Common |
| BulkEdit | Common |
| BulkExport | Common |
| EasyAdmin | Common, Cron |
| IiifServer | Common |
| ImageServer | Common |
| Log | Common |
| OaiPmhRepository | Common |
| Reference | Common |
| SearchSolr | Common, AdvancedSearch |
| UniversalViewer | Common |

## Inventory-Based Modules

You can also define modules per instance in the inventory so they are installed during initial deployment:

```yaml
# host_vars/<server>/main.yml
omeka_instances:
  my-instance:
    domain: omeka.example.edu
    nginx_port: 8081
    extra_modules:
      - EasyAdmin
      - CSSEditor
    extra_themes:
      - cozy
```

These are written to `.env` via the `env.j2` template during `deploy-instance.yml` and installed by the entrypoint on first container start.

## Verification

After installation, the playbook automatically verifies each module exists on disk and reports `INSTALLED` or `FAILED`. You can also check manually on the server:

```bash
# List installed modules
sudo ls /var/lib/docker/volumes/<instance>_omeka_files/_data/modules/

# Check container logs for installation output
sudo docker logs <instance>-php-1 2>&1 | grep -iE "module|extra"
```
