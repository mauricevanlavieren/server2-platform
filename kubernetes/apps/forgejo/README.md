# Forgejo — actief via Flux

Op 9 oktober 2026 met eigenaarakkoord geactiveerd op server2. Eén replica; aparte Flux-Kustomization met afhankelijkheden infrastructure en forgejo-secrets. Namespace/secrets worden door de secrets-bootstrap beheerd. PVC blijft via prune-uitzondering behouden.

Actuele gecontroleerde werking, beperkingen en eigenaarbootstrap: `../../../docs/server/forgejo-activation-verification.md`. Oorspronkelijk ontwerp: `../../../docs/server/forgejo-deployment-plan.md`.

Wijzig uitsluitend via GitOps. Bestaande bootstrap/gitops-voorbeelden blijven gesuspendeerde voorbeelden. Geen plaintext Secretwaarden of private sleutels in Git. GitHub blijft platformbron; geen kritieke gegevens zolang backups ontbreken. Local-path biedt geen harde 10Gi-quota.
