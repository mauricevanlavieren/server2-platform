# Disaster recovery

Statusdatum: 2026-10-15. Fase 2 publiceert alleen de GitHub-basis en documentatie. Geen serverwijziging, deployment, applicatiemigratie of back-upactivatie. Gewenste vervolgstappen zijn geen uitgevoerde configuratie.

Code is geen volledige back-up. Voor onafhankelijk herstel zijn Git-bundles met alle refs, benodigde LFS/releaseassets, OCI-images met digests, consistente appdata en afzonderlijk beveiligde herstelkeys nodig. Alleen een Git-bundle bevat geen registries, databases of geheime materialen.

Geplande volgorde: onafhankelijke beheeromgeving en sleuteltoegang, server3/mount/RAID-verificatie, geïsoleerd clusterfundament, coherente k3s-token/encryptieset of expliciet schone bootstrap, storage/dataherstel vóór writers, daarna gecontroleerde Flux/appstart. Geen actieve database overschrijven. Volledig server2-herstel op server4 vereist apart akkoord; nog niet bewezen. Server1 blijft buiten bereik.
