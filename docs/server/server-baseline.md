# Server Baseline

This document records the verified baseline configuration of `server2`.

It describes the state of the physical host before installation of the k3s
platform. Configuration that can be automated will progressively be moved into
the bootstrap automation in this repository.

## 1. Server Identity

| Item | Value |
|---|---|
| Hostname | `mau2` |
| Platform | HP EliteDesk 800 G2 SFF |
| Operating system | Ubuntu Server 24.04 LTS |
| Architecture | x86-64 |
| Administration | SSH |
| SSH alias | `server2` |

## 2. Hardware

### CPU

- Intel Core i5-6500
- 4 cores
- 4 threads

### Memory

- Approximately 8 GB RAM
- 4 GB swap (`/swap.img`)

### Storage

Primary disk:

- approximately 256 GB SSD
- GPT/UEFI boot
- LVM used for the Ubuntu root filesystem

Layout:

    sda
    ├── sda1   1G      FAT32    /boot/efi
    ├── sda2   2G      ext4     /boot
    └── sda3   ~235G   LVM
         └── ubuntu-vg/ubuntu-lv
             └── /

## 3. Firmware

System BIOS was upgraded during initial server preparation.

Before:

    HP N01 Ver. 02.17
    Release date: 2016-11-01

Current:

    HP N01 Ver. 02.60
    Release date: 2022-12-15

The installed version was verified from Ubuntu with:

    sudo dmidecode -s bios-version
    sudo dmidecode -s bios-release-date

Result:

    N01 Ver. 02.60
    12/15/2022

### BIOS update procedure

The official HP BIOS package for the EliteDesk 800 G2 SFF was used.

The BIOS binary used was:

    N01_0260.bin

The update media used a FAT32 USB device.

For BIOS Setup / Local Media updates, the BIOS binary was placed at:

    Hewlett-Packard/BIOS/new/N01_0260.bin

The SHA256 checksum of the source image and the copy in the HP BIOS directory
were verified to be identical before flashing.

Verified SHA256:

    4de4ebe062bae018c965722ecf8d21ba553865a6a88cc0e3c43a630cbdcbd81a

The update was performed through HP BIOS Setup using the local media update
function.

After the update Ubuntu booted successfully and BIOS version 02.60 was verified.

## 4. Network

Primary network interface:

    eno1

Server address:

    192.168.0.162

Default gateway:

    192.168.0.1

DNS:

    Primary:   192.168.0.10
    Secondary: 192.168.0.1

The server itself uses DHCP.

A DHCP reservation on the router provides the stable server address:

    MAC: A0:8C:FD:DC:84:0D
    IP:  192.168.0.162

This avoids maintaining a separate static IP configuration on the Ubuntu host.

## 5. Time Configuration

Timezone:

    Europe/Amsterdam

NTP synchronization is enabled and verified.

The hardware RTC remains in UTC.

## 6. SSH

Remote administration is performed using SSH public-key authentication.

Administrative workstation:

    ssh server2

The SSH alias resolves to:

    Host: 192.168.0.162
    User: mau

### SSH hardening

A dedicated SSH configuration fragment is used:

    /etc/ssh/sshd_config.d/00-homelab-hardening.conf

Configuration:

    PasswordAuthentication no
    PermitRootLogin no
    PubkeyAuthentication yes

Effective SSH configuration was verified after configuration.

SSH public-key login was tested before password authentication was disabled.

## 7. Firewall

Ubuntu UFW is enabled.

Policy:

    Incoming: deny
    Outgoing: allow

SSH is explicitly allowed.

At the initial host baseline, SSH was the only intentionally exposed
administrative service.

Firewall configuration will be reviewed again during k3s installation because
Kubernetes networking introduces additional networking requirements.

## 8. Automatic Updates

Ubuntu unattended upgrades are enabled.

Automatic package list updates and unattended security updates are configured.

Security updates are allowed from the appropriate Ubuntu security repositories.

Automatic distribution upgrades are not part of this configuration.

Major Ubuntu LTS upgrades will be performed deliberately rather than
automatically.

## 9. Host Security

### AppArmor

AppArmor is installed, loaded and enabled.

It will remain enabled unless a specific, documented compatibility requirement
requires a change.

### cgroups

The host uses cgroup v2.

This is suitable for the planned k3s/containerd platform.

## 10. Kubernetes Prerequisites

During the initial baseline inspection:

    net.ipv4.ip_forward = 0

and the following kernel modules were not loaded:

    overlay
    br_netfilter

These settings have intentionally not yet been changed manually.

Required Kubernetes host configuration will be implemented through the
bootstrap automation rather than through undocumented manual configuration.

## 11. Wake-on-LAN

The Ethernet adapter supports Wake-on-LAN.

Verified with:

    sudo ethtool eno1 | grep -i wake

Result:

    Supports Wake-on: pumbg
    Wake-on: g

`g` indicates Wake-on-LAN using a Magic Packet.

### Administration workstation

The administration laptop contains the command:

    wake-server2

which executes:

    wakeonlan A0:8C:FD:DC:84:0D

The helper is installed as:

    /usr/local/bin/wake-server2

Wake-on-LAN was successfully tested after upgrading the system BIOS to N01
02.60.

The server now powers on remotely and boots Ubuntu normally.

## 12. Current Baseline Status

Verified:

- [x] Ubuntu installed
- [x] OS updated
- [x] Server hardware inventoried
- [x] Stable IP through DHCP reservation
- [x] Timezone configured
- [x] NTP synchronized
- [x] SSH public-key authentication
- [x] SSH password authentication disabled
- [x] SSH root login disabled
- [x] UFW enabled
- [x] Automatic security updates enabled
- [x] AppArmor enabled
- [x] cgroup v2 verified
- [x] BIOS upgraded to N01 02.60
- [x] Wake-on-LAN enabled and tested

Not yet implemented:

- [ ] Automated host bootstrap
- [ ] Kubernetes kernel/network prerequisites
- [ ] k3s
- [ ] GitOps
- [ ] Cluster networking
- [ ] Persistent storage strategy
- [ ] Monitoring and alerting
- [ ] Backup automation
- [ ] Restore testing
- [ ] Disaster recovery automation

## 13. Automation Follow-up

The current baseline contains several settings that were initially configured
manually.

Where practical, these will be converted into idempotent bootstrap automation.

The intended model is:

    Fresh Ubuntu installation
             |
             v
    Minimal bootstrap
             |
             v
    Automated host configuration
             |
             v
            k3s
             |
             v
           GitOps
             |
             v
    Infrastructure + applications

The goal is that loss of the physical server does not require reconstructing
its configuration from memory or undocumented manual steps.
