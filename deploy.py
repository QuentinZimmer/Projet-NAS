import os
from gns_config_bot import GNSConfigBot

root_dir = os.path.dirname(os.path.abspath(__file__))
configs_gen_dir = os.path.join(root_dir, "configs_big_gen")
dynamips_dir = os.path.join(root_dir, "project-files", "dynamips")

bot = GNSConfigBot(configs_gen_dir, dynamips_dir)

print("Routeurs détectés :", bot.router_map)

bot.deploy_all()
