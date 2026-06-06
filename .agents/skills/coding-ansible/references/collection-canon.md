# Ansible collection canon

The collections worth standardizing on, by tech. Prefer the canonical namespace over keyword-search noise - Galaxy's modern backend does not expose a popularity sort, so the search results are not ranked by adoption.

- **Docker** - `community.docker` (modules) + role `geerlingguy.docker` (engine install, the single most-downloaded role on Galaxy).
- **Kubernetes** - `kubernetes.core` (the `k8s` module). For cluster bring-up itself, `geerlingguy.kubernetes` or `kubernetes_sigs.kubespray`.
- **AWS** - `amazon.aws` (official) + `community.aws`. Drive AWS through modules, not roles.
- **Terraform** - `cloud.terraform` (official, terraform module + state-as-inventory).
- **Prometheus** - `prometheus.prometheus` (the old cloudalchemy roles, handed over and bundling prometheus, alertmanager, node_exporter, blackbox).
- **Grafana** - `grafana.grafana` (Grafana Labs official, role + dashboards + `grafana_*` modules).
- **Datadog** - `datadog.dd` + role `datadog.datadog`. Vendor-owned.
- **New Relic** - `newrelic.newrelic_agents` + role `newrelic.newrelic-infra`.
- **PostgreSQL / MySQL** - `community.postgresql` / `community.mysql` + the geerlingguy roles.
- **Nginx** - `nginxinc.nginx_core` (F5 official) + role `geerlingguy.nginx` for the common case.
- **Hardening** - `devsec.hardening` (the dev-sec org, ssh/os/nginx/mysql CIS baselines).
- **HashiCorp** - `community.hashi_vault` (Vault API). Consul installs via `brianshumate.consul`.
- **Certs** - `community.crypto` (ACME modules), not a certbot role wrapper.

## Known gaps

- **Vector** has effectively no Galaxy presence - template the install yourself.
- **OpenTelemetry** is thin - `signalfx.splunk_otel_collector` is the most mature, otherwise roll the collector deploy.

## The registry

Ansible Galaxy (galaxy.ansible.com) is the open-source package index, running the Apache-2.0 `galaxy_ng` backend. Two content types:

- **Roles** - legacy `/api/v1/roles/`, download-ranked. Rank with `?order_by=-download_count`.
- **Collections** - `/api/v3/`, no public popularity sort. Rank by reputation, not the API.

Both are scrapeable without auth.
