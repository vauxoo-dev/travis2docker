#!/bin/bash
{{ entrypoint_commands_before }}
{% for entrypoint in entrypoints %}
{{ entrypoint }}
{% endfor %}
{{ entrypoint_commands_after }}
