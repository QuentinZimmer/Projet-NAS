## BIG_automatique — IPv4 MPLS Core avec OSPF & eBGP

# Objectif du projet

Automatisation complète d'une architecture MPLS (Multiprotocol Label Switching) avec :
- IGP OSPF dans le core
- eBGP entre PE (Provider Edge) et CE (Customer Edge)
- MPLS LDP en cœur de réseau

# Architecture

**Topologie :**
- **Core (AS 64500)** : R1 (PE) — R2 (P) — R3 (P) — R4 (PE)
- **Customers** :
  - R6 (CE, AS 65002) connecté à R1
  - R5 (CE, AS 65001) connecté à R4

**Protocoles :**
- **IGP** : OSPF (AS 64500, zone 0)
  - Loopbacks en 10.0.0.0/24 (/32 pour chaque routeur)
  - Liens inter-routeurs en 145.0.0.0/16
- **BGP** :
  - iBGP full-mesh entre PE via loopbacks
  - eBGP sur interfaces directes PE↔CE
- **MPLS/LDP** :
  - Activé sur tous les liens core (intra_as)
  - Désactivé sur interfaces PE↔CE (inter_as)

# Structure du projet

BIG_AUTOMATIQUE/
├── gen_configs.py        # Génération automatique des configs routeurs
├── gns_config_bot.py     # Déploiement automatique dans GNS3
├── deploy.py             # Script de lancement du déploiement
├── intents/
│   └── intent_big.json   # Intent file (topologie + politiques)
├── configs_big_gen/      # Configurations générées (R1.cfg, R2.cfg, ...)
├── project-files/
│   └── dynamips/         # Dossier Dynamips du projet GNS3
└── BIG_automatique.gns3  # Projet GNS3

# Lancement

## Prérequis

Adapter les chemins dans `deploy.py` :
```python
configs_gen_dir = r"C:\Users\TON_USER\GNS3\projects\NAS_automatique\BIG_automatique\BIG_automatique\configs_big_gen"
dynamips_dir = r"C:\Users\TON_USER\GNS3\projects\NAS_automatique\BIG_automatique\BIG_automatique\project-files\dynamips"
```

## Commandes de déploiement

### Option 1 : Déploiement automatique (recommandé)

**Étape 1** - Générer les configurations :
```bash
python gen_configs_ipv4.py
```

**Étape 2** - Déployer dans GNS3 :
```bash
python manual_deploy.py
```

Ce script copie les configurations générées (R1.cfg, R2.cfg, etc.) dans les fichiers startup-config des routeurs GNS3 (fichiers iX_startup-config.cfg).

**Étape 3** - Lancer GNS3, redémarrer les routeurs, et vérifier avec :
```bash
show ip interface brief
```

### Option 2 : Déploiement via Telnet (sans GNS3 bot)

Alternativement, si les routeurs sont déjà démarrés :
```bash
python deploy_telnet.py
```

Cela injecte les configurations directement via Telnet sur les adresses IP des routeurs.

### Commandes complètes en one-liner

Générer + déployer automatiquement :
```bash
python gen_configs_ipv4.py && python manual_deploy.py
```

## Fichiers générés

- `configs_big_gen/` : Configurations pour chaque routeur (R1.cfg, R2.cfg, ...)
- `intents/intent_big_ipv4.json` : Intent file définissant la topologie et les paramètres

## Notes importantes

⚠️ **Pourquoi `manual_deploy.py` ?**
- Le script `deploy.py` original détecte automatiquement les UUIDs des routeurs, mais peut se tromper
- `manual_deploy.py` utilise un mapping manuel qui a été vérifié et corrigé pour les UUIDs réels

⚠️ **Configuration startup-config**
- Ne pas ajouter `conf terminal` dans les startup-config Cisco Dynamips
- Le routeur charge déjà automatiquement en mode configuration au démarrage

