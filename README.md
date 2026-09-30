# Server2 Platform

Automation-first k3s homelab platform running on a dedicated HP EliteDesk 800 G2 SFF.

## Purpose

The goal of this repository is to provide a stable, secure, automated,
reproducible and recoverable Kubernetes platform.

Git is intended to become the single source of truth for both host configuration
and Kubernetes workloads.

Design principles:

- Automation first
- Infrastructure as Code
- GitOps
- Reproducible configuration
- Minimal manual administration
- Secure by default
- Automated monitoring and alerting
- Automated backups
- Tested recovery procedures
- Configuration drift prevention

The target recovery model is:

Server → minimal bootstrap → automation → k3s → GitOps → complete platform

## Platform

### Hardware

- HP EliteDesk 800 G2 SFF
- Intel Core i5-6500
- 8 GB RAM
- 256 GB SSD
- Ethernet interface: `eno1`

### Operating System

- Ubuntu Server 24.04 LTS
- systemd
- AppArmor
- cgroup v2
- LVM
- UEFI

### Firmware

- BIOS: HP N01 Ver. 02.60
- BIOS release date: 2022-12-15
- Wake-on-LAN enabled

## Network

| Component | Value |
|---|---|
| Hostname | `mau2` |
| Server IP | `192.168.0.162` |
| Gateway | `192.168.0.1` |
| Interface | `eno1` |
| Address assignment | DHCP reservation |
| Primary DNS | `192.168.0.10` |
| Secondary DNS | `192.168.0.1` |

The server uses DHCP. Its address is kept stable through a DHCP reservation on
the router rather than a static address configured on the host.

## Security Baseline

Current host security includes:

- SSH public-key authentication
- SSH password authentication disabled
- SSH root login disabled
- UFW enabled
- Default incoming traffic denied
- Automatic security updates enabled
- AppArmor enabled
- NTP/time synchronization enabled

## Remote Management

SSH access from the administration workstation:

    ssh server2

Wake-on-LAN:

    wake-server2

Wake-on-LAN uses a Magic Packet and has been successfully tested after the BIOS
upgrade to N01 02.60.

## Planned Architecture

    GitHub
       |
       +-- bootstrap/
       |      |
       |      +--> Ubuntu host configuration
       |      +--> security
       |      +--> packages
       |      +--> k3s bootstrap
       |
       +-- kubernetes/
              |
              +--> GitOps controller
                     |
                     +--> infrastructure
                     +--> applications

The Kubernetes platform will use k3s with containerd.

A GitOps controller will reconcile the desired state stored in this repository
with the live Kubernetes cluster.

## Repository Structure

    server2-platform/
    ├── bootstrap/
    │   ├── ansible/
    │   └── scripts/
    │
    ├── kubernetes/
    │   ├── infrastructure/
    │   │   ├── gitops/
    │   │   ├── networking/
    │   │   ├── storage/
    │   │   ├── security/
    │   │   ├── monitoring/
    │   │   └── backup/
    │   └── apps/
    │
    ├── docs/
    │   ├── architecture/
    │   ├── operations/
    │   └── server/
    │
    └── scripts/

Directories will be created when they contain actual configuration or
documentation rather than creating an empty directory tree in advance.

## Current Status

### Server foundation

- [x] Ubuntu Server installed
- [x] OS fully updated
- [x] DHCP reservation configured
- [x] SSH key authentication configured
- [x] SSH hardened
- [x] UFW configured
- [x] Automatic security updates configured
- [x] Timezone and NTP configured
- [x] AppArmor verified
- [x] cgroup v2 verified
- [x] BIOS upgraded from N01 02.17 to N01 02.60
- [x] Wake-on-LAN configured and tested
- [ ] Host bootstrap automated
- [ ] k3s installed
- [ ] GitOps configured
- [ ] Networking/Ingress configured
- [ ] Persistent storage configured
- [ ] Monitoring and alerting configured
- [ ] Backup and restore configured
- [ ] Disaster recovery procedure tested

## Availability

This platform currently runs on a single physical server.

Kubernetes can provide application-level self-healing, but a single-node
cluster does not provide infrastructure-level high availability. Host failure
therefore remains a platform outage until the server is recovered or rebuilt.
