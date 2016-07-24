FROM {{ image  }}
COPY {{ entrypoint_path }} /entrypoint.sh
ENTRYPOINT /entrypoint.sh

{% if env %}ENV {{ env }}{% endif %}

{% for src, dest in copies %}
COPY {{ src }} {{ dest }}
{% endfor %}

{% for run in runs %}
RUN {{ run }}
{% endfor %}
