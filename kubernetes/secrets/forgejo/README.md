# Forgejo secrets — inactive staging

READY: namespace, SOPS-encrypted runtime/TLS Secrets and repository .sops.yaml. DISABLED: no active Flux reference. Both bootstrap Flux examples remain suspend=true. Private CA key, age identity and unencrypted TLS key remain outside Git.

This directory is the future namespace owner. The app Kustomization no longer includes its namespace.yaml to avoid two Flux reconciliations competing for ownership; that old file remains unreferenced as a reference. Activate namespace/secrets first through a separate approved Flux change, then app with dependency on forgejo-secrets. Do not kubectl apply these encrypted manifests.

Local SOPS decryption validation succeeded in memory; no plaintext shown/written to repository. The Kubernetes age bootstrap key is not installed. There is no operational proof of Flux decryption, no app deployment, no certificate served and no backup.

Encrypted Git ciphertext is publishable after separate review/commit approval. Current keys exist only on laptop; owner accepted that loss risk. Never commit age.key, ca.key.pem or forgejo.key.pem. System trust was installed by owner and openssl verification passed; browser trust remains unverified.
