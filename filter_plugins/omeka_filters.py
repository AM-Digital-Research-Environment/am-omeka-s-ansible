"""Custom Jinja2 filters for Omeka S Ansible playbooks."""


def instance_port(instance_config):
    """Extract the port number from an instance config."""
    return instance_config.get('nginx_port', 8080)


def enabled_instances(omeka_instances):
    """Filter instances to only those with backup_enabled=true."""
    return {
        name: config
        for name, config in omeka_instances.items()
        if config.get('backup_enabled', False)
    }


class FilterModule:
    """Custom filters for Omeka S management."""

    def filters(self):
        return {
            'instance_port': instance_port,
            'enabled_instances': enabled_instances,
        }
