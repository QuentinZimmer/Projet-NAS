from gns_config_bot import GNSConfigBot

configs_gen_dir = r"C:\Users\cpoud\GNS3\projects\NAS_automatique\BIG_automatique\BIG_automatique\configs_big_gen"
dynamips_dir = r"C:\Users\cpoud\GNS3\projects\NAS_automatique\BIG_automatique\BIG_automatique\project-files\dynamips"

bot = GNSConfigBot(configs_gen_dir, dynamips_dir)

print("Routeurs détectés :", bot.router_map)

bot.deploy_all()
