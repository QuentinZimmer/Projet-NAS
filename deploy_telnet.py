import telnetlib
import time
import os

HOST = "127.0.0.1"

# ✅ A remplir avec les ports de console GNS3
ROUTER_TELNET_PORTS = {
    "R1": 5004,
    "R2": 5005,
    "R3": 5006,
    "R4": 5007,
    "R5": 5008,
    "R6": 5009,
    "R7": 5010,
    "R8": 5011,
    "R9": 5012,
    "R10": 5013,
    # si tu ajoutes R11 R12 R13 :
    "R11": 5000,
    "R12": 5001,
    "R13": 5002,
}

CONFIG_DIR = "configs_big_gen"


def clean_lines_for_cli(cfg_text: str):
    """
    Nettoyage : on enlève les lignes inutiles, et on évite les doublons
    """
    lines = []
    for raw in cfg_text.splitlines():
        line = raw.rstrip()

        # skip commentaires vides
        if line.strip() == "":
            continue

        # skip markers inutiles
        if line.strip().startswith("!"):
            continue

        # skip boot markers & autres
        if "boot-start-marker" in line or "boot-end-marker" in line:
            continue

        # évite "end" au milieu
        if line.strip() == "end":
            continue

        # évite "conf terminal" si déjà injecté
        if line.strip() in ("conf terminal", "configure terminal"):
            continue

        lines.append(line)
    return lines


def deploy_router(router_name: str):
    port = ROUTER_TELNET_PORTS[router_name]
    cfg_path = os.path.join(CONFIG_DIR, f"{router_name}.cfg")

    if not os.path.isfile(cfg_path):
        print(f"[SKIP] Fichier manquant: {cfg_path}")
        return

    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg_text = f.read()

    cfg_lines = clean_lines_for_cli(cfg_text)

    print(f"[INFO] Connexion Telnet à {router_name} sur {HOST}:{port} ...")
    tn = telnetlib.Telnet(HOST, port, timeout=10)

    time.sleep(1)
    tn.write(b"\r\n")

    # ✅ Passe en enable
    tn.write(b"enable\r\n")
    time.sleep(0.2)

    # If an enable password is set via environment, send it
    en_pw = os.environ.get("ENABLE_SECRET", None)
    if en_pw:
        try:
            tn.read_until(b"Password:", timeout=1)
        except Exception:
            pass
        tn.write(en_pw.encode("utf-8") + b"\r\n")
        time.sleep(0.5)

    # ✅ Configure terminal
    tn.write(b"conf t\r\n")
    time.sleep(0.5)

    # ✅ Envoi ligne par ligne
    for line in cfg_lines:
        tn.write(line.encode("utf-8") + b"\r\n")
        time.sleep(0.05)  # mini pause, sinon IOS rate des lignes

    # ✅ Fin + sauvegarde
    tn.write(b"\r\n")
    tn.write(b"end\r\n")
    time.sleep(0.5)
    tn.write(b"wr mem\r\n")
    time.sleep(1.0)
    tn.write(b"\r\n")
    time.sleep(0.2)
    tn.close()

    print(f"[OK] {router_name} déployé via Telnet.")


def main():
    for r in ROUTER_TELNET_PORTS.keys():
        deploy_router(r)


if __name__ == "__main__":
    main()
