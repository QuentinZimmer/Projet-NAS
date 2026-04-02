#!/usr/bin/env python3
import os
import shutil

# Mapping des routeurs à leurs emplacements GNS3
mappings = {
    'R1': ('2d7dba40-411b-455f-82d9-3de14599e392', 'i1_startup-config.cfg'),
    'R2': ('a667a9d3-04c3-4565-982e-80ead5c948d6', 'i2_startup-config.cfg'),
    'R3': ('9a0e862d-d423-4877-9c7a-1f16bd6cdcd9', 'i3_startup-config.cfg'),
    'R4': ('a23965b7-6f76-48d6-928b-70a84247114a', 'i4_startup-config.cfg'),
    'R5': ('675865fe-d280-401d-b042-1ad7c90700c3', 'i5_startup-config.cfg'),
    'R6': ('4b24edd0-cccd-47e4-a80f-6b9bdfa0ea7f', 'i6_startup-config.cfg'),
    'R7': ('ca70428b-342e-4c5f-ba17-4bfc78070771', 'i7_startup-config.cfg'),
    'R8': ('e7715d81-8039-4743-8c72-7e193b252613', 'i8_startup-config.cfg'),
}

base_dir = os.path.dirname(os.path.abspath(__file__))
configs_dir = os.path.join(base_dir, 'configs_big_gen')
dynamips_dir = os.path.join(base_dir, 'project-files', 'dynamips')

for router, (uuid, cfgfile) in mappings.items():
    src = os.path.join(configs_dir, f'{router}.cfg')
    dst = os.path.join(dynamips_dir, uuid, 'configs', cfgfile)
    
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f'[OK] {router} -> {dst}')
    else:
        print(f'[ERROR] {src} not found')
