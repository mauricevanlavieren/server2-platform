# Architectuur

Statusdatum: 2026-10-15. Fase 2 publiceert alleen de GitHub-basis en documentatie. Geen serverwijziging, deployment, applicatiemigratie of back-upactivatie. Gewenste vervolgstappen zijn geen uitgevoerde configuratie.

Server2-hostbeheer, Flux/Kubernetes en huidige applicatieconfiguratie. Toekomstige bronimports vereisen apart akkoord.

- [server1-platform](https://github.com/mauricevanlavieren/server1-platform): Historische server1-configuratie en demo-app; bestaande paden behouden. Geen live beheer of verificatie van server1.
- [server2-platform](https://github.com/mauricevanlavieren/server2-platform): Server2-hostbeheer, Flux/Kubernetes en huidige applicatieconfiguratie. Toekomstige bronimports vereisen apart akkoord.
- [server3-backup](https://github.com/mauricevanlavieren/server3-backup): Server3-back-updoel, hostbeleid en herstelprocedures. Deze repository bevat voorlopig uitsluitend documentatie.
- [homelab-architecture](https://github.com/mauricevanlavieren/homelab-architecture): Centrale index, afhankelijkheden, ontwerpbesluiten en AI-handover; geen deploybare configuratie.

De centrale architectuur legt eigenaarschap en herstelvolgorde vast. Beheerde configuratie blijft in de serverrepo van de eigenaar; geen tweede beheerkopie in de architectuurrepo.
