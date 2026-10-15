# Security status — staging only; deployment NO-GO

Recorded 13 October 2026. The phase-2 image scan reported **48 High package/advisory matches across 12 unique High advisories, 3 Unknown, 60 Medium and 61 Low; no Critical matches**. No High/Unknown findings accepted. CI blocks these severities, unexpected severities and missing scan evidence. No ignore-unfixed/suppressions.

Exact official Python 3.13.16-slim-trixie linux/amd64 base: sha256:8fb4cfa1a2616d7b8e0c2175cc6ad68f5729c34ea8488c0b360d2934b7be9024. Findings include util-linux, ACL, ncurses, systemd libraries, Perl, msgpack, setuptools and urllib3. No external application packages are used; absence of imports does not prove vulnerable base code is inapplicable. Non-root/read-only/capability restrictions mitigate exposure, without clearing advisories.

Independent publisher signature and build-provenance verification are missing. The SBOM is derived scanner inventory, not signed publisher evidence. Third-party SBOM warnings and incomplete embedded/native coverage remain limitations. No application image is published; no final registry digest exists. Local Docker ImageID is not a registry manifest digest.

Deployment requires specific High/Unknown resolution or explicit per-advisory owner risk acceptance, fresh final-artifact scan/provenance checks, separate image-publication approval, real registry digest, current server2 capacity/health, storage/fsGroup/backup and CNI enforcement verification, admission and probe/resource validation. IPv6 isolation is not proven. Accepted IPv4 test evidence retains 19 missing counter correlations. No application authentication; operator-only loopback port-forward is the proposed access model. The stdlib server is a restricted demo, not a general production server.

Kubernetes/Flux files belong only in server2-platform and remain suspended/disconnected. CI has no registry publication or deployment actions. No real emails, credentials, external mail/AI connection or sending capability. Generated logs/SBOMs/test databases remain outside source commits. Complete timestamped evidence stays in the locally delivered phase-2 package. Staging source is not risk acceptance.

## Limited packaging-removal revision

The same official Python 3.13.16-slim-trixie amd64 digest is retained. Only the unused pip installer directory, pip-26.2.1.dist-info, pip/pip3/pip3.13 entrypoints and ensurepip (including its bundled pip wheel) are removed. No application dependency, standard-library runtime function used by Postkamer, configuration, resource limit or healthcheck is changed. The existing CI container regression now verifies installer/module/wheel/entrypoint absence.

The controlled local scan using the same scanner/advisory dataset reports **47 blocking package/advisory matches across 11 unique IDs: 44 High matches across 8 unique High IDs, and 3 Unknown IDs**. Four pip-inventory advisories disappear: GHSA-6v7p-g79w-8964, CVE-2025-47273, CVE-2026-97687 and CVE-2026-97689. These counts do not imply 47 independent vulnerabilities or a safe release. Security thresholds and the gate implementation remain unchanged; the gate still exits 1 (FAIL). CI with a refreshed database must independently confirm its own results.

All remaining OS advisories and provenance/storage/CNI/deployment conditions above remain open. No CVE suppression, risk acceptance or image publication. Removing ensurepip deliberately disables installing/reintroducing pip in the runtime image. Future dependencies must be introduced in a reviewed build stage before stripping packaging, with dependency pins and fresh security/functional validation; do not install packages into a running container. Python's runtime and application remain testable without pip.

## Hardened test-MVP candidate — exception proposal only

The official Debian trixie-security liblzma5 5.8.1-1+deb13u2 update is checksum-pinned and installed before stripping unused packaging. Its package SHA256 is b38acab30f295bf1066a6632e31cbd0a1980f2924b38040cda131d5dea5384ec. The upstream repository signature, Packages.xz hash and package hash were checked locally; the trusted archive key came from the pinned official base, so this is not independent publisher identity verification. CI downloads the same locked package before a network-free build. The binary is excluded from Git.

Unused mount, umount, nsenter, unshare, setpriv, su, runuser and chroot helpers are removed, and all remaining regular /usr files have setuid/setgid bits stripped. Required Python/native libraries remain. Non-root, read-only filesystem, capability restrictions, probes and persistence requirements remain unchanged.

The controlled candidate scan reports **45 blocking matches: 44 High and one Unknown, across nine unique advisories**. The nine IDs and their individual applicability/fix limitations are recorded in docs/TEST-MVP-ADVISORIES.csv. DSA-6549-1 and TEMP-1147318-639065 are resolved by the official liblzma update. Helper removal mitigates some util-linux paths, without clearing vulnerable shared-library packages or proving every native path unreachable. Scanner findings are not suppressed.

Independent base-image publisher signature/provenance verification is still missing. A locally generated SBOM is inventory evidence, not signed publisher provenance. The CI securitygate is unchanged and must continue FAIL for these findings. No automatic publication/deployment or security-bypass job is added. Publication approval is separate from risk acceptance.

**Proposed exception, NOT ACTIVE:** one isolated server2 replica of the exact reviewed artifact; only 40 synthetic messages and fictitious drafts; operator-only localhost access; no external mail, AI, internet egress or real data; non-root, no escalation, drop ALL, read-only root, 250m CPU/256Mi RAM. Maximum seven days starting only after separately approved deployment. No production or other-workload acceptance. Stop on isolation loss, new material remote/Critical risk, resource problems or platform disruption. At expiry stop or obtain a new decision. Kubernetes does not automatically stop a Deployment when this written exception expires.

Release readiness still requires a verified GHCR manifest digest, private pull authentication outside Git, current server2 capacity/health, reviewed IPv4 enforcement and explicit treatment of unproven IPv6 isolation, storage ownership/PVC validation, and separate GitOps/deployment approval. Namespace and PVC retention must protect drafts during rollback; no permanent installation is approved here.
