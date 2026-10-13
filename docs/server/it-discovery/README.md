# Kompas — IT Discovery & Advisory

**Actuele v1-status:** zie [V1.md](V1.md). Hostcollector, backupdashboard, persistente workflow, zeven rapporttypen en Linux-toolkit zijn inmiddels operationeel. Oudere PARTIAL/BLOCKED-notities hieronder beschrijven eerdere mijlpalen; V1.md geeft de actuele beperkingen. Interne TLS/login/Dashy, SMART zonder smartctl en telefoontransport blijven open.

Status: **PARTIAL, local MVP working; isolated server deployment activated after actual owner-run backup/restore PASS**. Runtime acceptance remains separate from prepared manifests.

Local start: `python3 -B applications/it-discovery/app.py`; open http://127.0.0.1:8780. Stdlib-only Python/SQLite, no external dependencies, external AI or system execution. Local collector checks the server2 endpoint is exactly 192.168.0.162:6443 before metadata requests. No LAN scans. Kubernetes collector allows only fixed read paths: nodes, namespaces, pods, services, PVCs, deployments, node metrics. It never collects Secrets, pod env/commands, ConfigMaps or customer data. SQLite observations remain outside Git. Demo dataset separated by dataset flag, which is not a multi-tenant security boundary. Operator-loopback access only; Host and write-Origin allowlists. No production readiness claim.

UI: current assets, metadata topology/drill-down, CPU/RAM history (60s collection, 14d retention), read-only errors/audit, fictional MKB, deterministic advice and six Markdown reports. JSON/CSV import requires synthetic attestation and writes only demo assets; exports protect spreadsheet formula prefixes. Intake recording works; full approval/execution workflow remains PARTIAL. No generic command/production-execution endpoint.

Existing /home/mau/platform-status-api is an Express status stub and remains unchanged; it does not provide discovery, storage, topology or advisory integration. Custom code is limited to those domain/integration gaps. Dashy remains unchanged pending safe integration with a deployed endpoint. Postkamer is paused for development, never reconfigured by this project.

## Resource budget

Observed baseline: i5-6500, four cores, about 7.6GiB RAM; about6GiB available, 209GiB free disk. New MVP budget requests25m/64Mi, limits250m/256Mi, PVC1Gi; host backup quota one CPU/768Mi only while running. These are budgets, not measured deployment usage. Existing CPU limits already oversubscribed. No heavy local LLM, NetBox, SIEM or observability stack.

Monitoring comparison: Beszel is a Go hub+agent suited to lightweight host history, but still adds a host agent and protected credential/bootstrap; Uptime Kuma provides availability checks with its own persistent DB and setup; compact Prometheus plus exporters/dashboard adds multiple services and retention overhead. First reuse existing Metrics Server with integrated SQLite history; dedicated Beszel/availability alerts and SMART/disk monitoring remain PARTIAL until backup/root gate. No untested memory numbers or uptime alerts claimed. Sources: https://beszel.dev/guide/getting-started , https://github.com/louislam/uptime-kuma/wiki/How-to-Install . NetBox's PostgreSQL/Redis/worker stack is not justified for one node: https://github.com/netbox-community/netbox/blob/main/docs/installation/index.md .

## GitOps staging

`kubernetes/apps/it-discovery` renders offline. `kubernetes/clusters/server2/it-discovery.yaml` is activated in cluster-root for this project only. Runtime is cgr.dev/chainguard/python@sha256:3e56a2973d429d5bf28d8dd99f929ea6344b0bf054c432f09cf579f747ee3114. Trivy reports zero findings; Cosign verified vendor signer and issuer. Python 3.15 runtime passes all nine app tests. Process-scoped amd64 seccomp guard denies AF_INET6 socket/socketpair, rejects other ABI, verifies base seccomp/no-new-privileges/no capabilities and installs before threads/exec. No global profile changes. Local guarded-runtime smoke PASS; server acceptance pending. Never reuse Postkamer's nine-advisory exception for this project. Source ConfigMap is immutable/content-hashed. Runtime deployment must preserve non-root/read-only/no-escalation/RuntimeDefault/dropALL, one writer and PVC. RBAC get/list only, no Secrets, exec, node-proxy or writes. NetworkPolicy ingress deny, egress only Kubernetes API IPv4 service/node targets; IPv6 enforcement remains unproven, not a complete isolation claim. No public Ingress/NodePort/LB. Host collector, auth/multi-tenant, cert/availability alerting remain unimplemented.

After backup/restore PASS: verify image/digest and security, resolve app-scoped IPv6 policy if needed, activate only own Flux Kustomization, test Ready/collection/PVC/replacement, port-forward 127.0.0.1:8780 to service8080. Activation is declarative; verify actual Ready/collection/persistence before claiming success.

## Backup and restore

Owner-only installer: `python3 -I -B operations/it-discovery-backup/install-backup.py --maintenance-approved`, only after explicit Forgejo maintenance consent. Hidden sudo input over SSH to fixed server2. Restic from maintained Ubuntu packages, no service auto-restarts requested. Root-only password and encrypted same-disk repo /var/backups/restic; never Git. Daily03:30UTC timer with 7daily/4weekly/3monthly retention; locking, 15GiB free-space gate, systemd failure recovery. Initial real encrypted backup/isolated restore must PASS before timer enablement/new risky deployments.

k3s SQLite uses Online Backup API, validated quick_check; includes server token/certificates/configuration in root-only encrypted backup. Forgejo briefly suspended/scaled0 only during consistent data capture, then restored in finally and systemd ExecStopPost; worker records prior suspend/replicas for recovery. Source data is never replaced by a restore test. Postkamer SQLite is backed up read-only without stop/reconfiguration. Isolated restore compares file hashes/UID/GID, SQLite integrity and Git fsck. This is a filesystem/data restore proof, not a full booted k3s or Forgejo disaster-recovery proof. Local same-disk repository DOES NOT protect against disk/host loss. Arrange owner off-host password escrow and later off-host backup.

Recovery from interrupted maintenance: root `python3 /opt/it-discovery-backup/backup-run.py --recover` restores ONLY Forgejo replicas and original suspend state. For disaster restore, stop and obtain explicit approval first; restore into an isolated root-only directory, verify integrity and ownership, plan downtime and preserve current data. Restore k3s state.db plus ORIGINAL token/config only with supported datastore/versions; no live production DB overwrite. Restore Forgejo files to approved PVC with source UID/GID/modes; validate app in isolation before cutover. Verify DNS/Flux/apps afterward. Secrets/password values must never be printed in recovery logs.

## Postkamer exception

Hard deadline20 October2026 17:19:30UTC, Maurice responsible. No automatic stop or extension. A local thread reminder was created to warn before deadline. Never stop early or migrate/extend Postkamer without owner approval.

## Remaining gates

Owner interactive sudo, explicit short Forgejo maintenance approval, actual backup/restore proof, verified new runtime, deployment/monitoring/persistence, controlled Dashy-link integration. Phone notifications require owner-selected external account/token and explicit external processing consent. No actual external notification configured.

Backup correction: first owner run stopped before SQLite snapshot/Forgejo pause because the server tree contains runtime Unix socket kine.sock. Original copy failure reproduced locally. Exclude only this exact socket at k3s server root, verify its socket type, retain unknown-special-file failure. No successful server backup/restore claimed until rerun.

Restore verification correction: owner evidence shows 132 files, no missing/ownership/symlink/SQLite-integrity failures and one 32KiB SQLite runtime-sidecar mismatch. Restic dump matches staging but not restored sidecar. Interleaved database opens could mutate restored shared memory; exact historical writer is not proven. Hash all files first, then open databases for integrity checks. Snapshot connections close explicitly and use DELETE journal mode. No sidecar hash exclusions or gate relaxation. Offline live-WAL snapshot/restore test PASS; new server backup/restore still required.

Owner restore evidence 2026-10-13: PASS at Unix timestamp1791921664.3130832; 130 file hashes/owners verified, SQLite integrity PASS, Git fsck PASS, uncovered PVCs empty. Service Result=success/ExecMainStatus=0 and timer active independently verified. Same-disk/off-host-loss limitation remains. Minimal public status cannot yet be read because its parent directory is root-only; backup success does not imply dashboard integration.

Rollback: set only it-discovery replicas to0 via Git, keep PVC/namespace (prune disabled). Remove only own Flux Kustomization/app declarations after approval; retain inventory PVC until explicit deletion approval. Local access: kubectl --context server2 -n it-discovery port-forward --address 127.0.0.1 service/it-discovery 8780:8080 ; use http://127.0.0.1:8780 (stop local demo first to free port).
