# Passage à IPv4 MPLS Core — Changelog

## 📋 Résumé

Le projet a été modernisé pour passer de la topologie IPv6 complexe à une architecture IPv4 simplifiée et plus réaliste basée sur **MPLS avec OSPF IGP et eBGP PE-CE**.

## ✅ Changements effectués

### 1. **Topologie simplifiée**
- ❌ Supprimé : R7-R13 (ancien réseau avec iBGP complexe)
- ✅ Conservé : R1, R2, R3, R4, R5, R6

**Nouvelle topologie :**
```
R6 (CE)
  |
  └─ R1 (PE) ─── R2 (P) ─── R3 (P) ─── R4 (PE) ─── R5 (CE)
     AS 65002          AS 64500            AS 65001
```

### 2. **Fichiers créés**
- `intents/intent_big_ipv4.json` — Intent file IPv4 avec topologie linéaire
- `gen_configs_ipv4.py` — Script de génération IPv4 avec OSPF, MPLS, eBGP

### 3. **Protocoles activés**

#### OSPF (IGP Core)
- Process ID: 1
- Area: 0
- Routeurs: R1, R2, R3, R4
- Activation: sur interfaces `intra_as` uniquement

#### MPLS LDP
- Global: activé sur tous les PE et P
- Par interface:
  - ✅ Interfaces core (R1↔R2, R2↔R3, R3↔R4)
  - ❌ Interfaces PE↔CE (R1↔R6, R4↔R5)

#### BGP
- **iBGP** (PE-PE):
  - R1 ↔ R4 via loopbacks (10.0.0.0/24)
  - Mode: full-mesh avec `next-hop-self`
  
- **eBGP** (PE-CE):
  - R1 ↔ R6 (AS 65002)
  - R4 ↔ R5 (AS 65001)
  - Via interfaces directes

### 4. **Adressage IPv4**
```
Loopbacks:
- Core (AS 64500): 10.0.0.1 à 10.0.0.4 /32
- R5 (AS 65001): 192.168.1.1 /32
- R6 (AS 65002): 192.168.2.1 /32

Liens (145.0.0.0/16):
- R1↔R2: 145.0.1.0/24
- R2↔R3: 145.0.2.0/24
- R3↔R4: 145.0.3.0/24
- R1↔R6: 145.0.4.0/24
- R4↔R5: 145.0.5.0/24
```

### 5. **Projet GNS3 nettoyé**
- ❌ Supprimés : Dossiers UUID pour R7-R13
- ✅ Conservés : Dossiers pour R1-R6
- ❌ Supprimés : Fichiers logs orphelins (dynamips_i7_*.txt, etc.)
- ✅ Mis à jour : BIG_automatique.gns3 (nœuds et liens)

### 6. **Documentation mise à jour**
- README.md : Architecture et commandes launch
- CHANGELOG_IPv4.md : Ce fichier

## 🚀 Utilisation

### Générer les configurations

```bash
cd c:\Users\cpoud\GNS3\projects\NAS_automatique\BIG_automatique\BIG_automatique
python gen_configs_ipv4.py
```

Résultat :
- `configs_big_gen/R1.cfg` — Configuration générée pour R1
- `configs_big_gen/R2.cfg` — Configuration générée pour R2
- ... (R3.cfg, R4.cfg, R5.cfg, R6.cfg)

### Déployer dans GNS3

```bash
python gns_config_bot.py
```

### Vérifier une config

```bash
cat configs_big_gen/R1.cfg
```

Attendu : Config IPv4 avec OSPF, MPLS, BGP

## 🔍 Validation

✅ **Tests effectués:**
1. Intent file JSON valide
2. Génération configs R1-R6 réussie
3. Structure BGP correcte (iBGP PE↔PE, eBGP PE↔CE)
4. MPLS sur tous liens core, désactivé PE↔CE
5. OSPF sur tous liens core
6. Loopbacks correctement alloués

## 📝 Notes importantes

- `gen_configs.py` (IPv6) est conservé pour compatibilité mais ne doit plus être utilisé
- `gen_configs_ipv4.py` remplace entièrement la génération automatique
- `gns_config_bot.py` fonctionne avec les deux versions (détecte les routers)
- `deploy_telnet.py` reste compatible

## 🔧 Fichiers clés

| Fichier | Rôle |
|---------|------|
| `gen_configs_ipv4.py` | Génération configs IPv4 |
| `intents/intent_big_ipv4.json` | Définition topologie IPv4 |
| `configs_big_gen/` | Configs générées |
| `gns_config_bot.py` | Déploiement dans GNS3 |
| `BIG_automatique.gns3` | Projet GNS3 (nettoyé) |

---

**Version:** IPv4 MPLS Core v1.0  
**Date:** Mars 2026  
**Statut:** ✅ Production-ready
