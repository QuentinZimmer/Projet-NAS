"""
Sync GNS3 topology file with intent.json
Automatically creates GNS3 physical links based on intent.json definitions
"""

import json
import uuid
from collections import defaultdict

# Router UUID mappings
ROUTER_UUIDS = {
    'R1': '9c7283d4-7cd9-4ec5-95f0-a723b7eb7d99',
    'R2': 'eedd683d-9376-406f-9437-b82ec187624a',
    'R3': '11c5d8ee-18ee-4471-ba5a-7fe7e57c2191',
    'R4': '106e1cf3-6058-4633-9c26-03d239835839',
    'R5': '038c1f3a-ed4a-4f08-8d0f-00fb12e2be31',
    'R6': '8736b5df-9ae9-4de0-8bf8-32a934b5fd55',
}

# Gateway interface mappings (which adapter number for each link type)
# Format: (router_role, interface_name) -> adapter_number
# adapter 0 = f0/0; adapter 1 = g1/0; adapter 2 = g2/0
INTERFACE_ADAPTER_MAP = {
    'R1': {'f0/0': 0, 'g1/0': 1, 'g2/0': 2},
    'R2': {'f0/0': 0, 'g1/0': 1, 'g2/0': 2},
    'R3': {'f0/0': 0, 'g1/0': 1, 'g2/0': 2},
    'R4': {'f0/0': 0, 'g1/0': 1, 'g2/0': 2},
    'R5': {'f0/0': 0, 'g1/0': 1, 'g2/0': 2},
    'R6': {'f0/0': 0, 'g1/0': 1, 'g2/0': 2},
}

def load_intent():
    """Load intent.json"""
    with open('intents/intent_big_ipv4.json', 'r') as f:
        return json.load(f)

def load_gns3():
    """Load GNS3 file"""
    with open('BIG_automatique.gns3', 'r') as f:
        return json.load(f)

def save_gns3(data):
    """Save GNS3 file"""
    with open('BIG_automatique.gns3', 'w') as f:
        json.dump(data, f, indent=4)

def extract_router_and_interface(connection_def):
    """Extract router name and interface from connection definition
    
    Examples:
    - "R1_g2/0" -> ("R1", "g2/0")
    - "R6_g1/0" -> ("R6", "g1/0")
    """
    if '_' in connection_def:
        parts = connection_def.rsplit('_', 1)
        return parts[0], parts[1]
    return None, None

def get_adapter_number(router, interface_name):
    """Convert interface name to adapter number
    
    g1/0 -> 1 (GigabitEthernet adapter 1)
    g2/0 -> 2 (GigabitEthernet adapter 2)
    f0/0 -> 0 (FastEthernet adapter 0)
    """
    if interface_name.startswith('g'):
        return int(interface_name[1])
    elif interface_name.startswith('f'):
        return int(interface_name[1])
    return 0

def create_gns3_link(node1_id, adapter1, node2_id, adapter2, gw1_name='', gw2_name=''):
    """Create a GNS3 link structure"""
    return {
        'filters': {},
        'link_id': str(uuid.uuid4()),
        'link_style': {},
        'nodes': [
            {
                'adapter_number': adapter1,
                'label': {
                    'rotation': 0,
                    'style': 'font-family: TypeWriter;font-size: 10.0;font-weight: bold;fill: #000000;fill-opacity: 1.0;',
                    'text': gw1_name if gw1_name else f'adapter{adapter1}',
                    'x': 62,
                    'y': 49
                },
                'node_id': node1_id,
                'port_number': 0
            },
            {
                'adapter_number': adapter2,
                'label': {
                    'rotation': 0,
                    'style': 'font-family: TypeWriter;font-size: 10.0;font-weight: bold;fill: #000000;fill-opacity: 1.0;',
                    'text': gw2_name if gw2_name else f'adapter{adapter2}',
                    'x': 3,
                    'y': -5
                },
                'node_id': node2_id,
                'port_number': 0
            }
        ],
        'suspend': False
    }

def link_exists(gns3_data, node1_id, node2_id):
    """Check if a link already exists between two nodes"""
    for link in gns3_data['topology']['links']:
        nodes = link['nodes']
        if ((nodes[0]['node_id'] == node1_id and nodes[1]['node_id'] == node2_id) or
            (nodes[0]['node_id'] == node2_id and nodes[1]['node_id'] == node1_id)):
            return True
    return False

def main():
    print("=== GNS3 Topology Synchronizer ===\n")
    
    intent = load_intent()
    gns3 = load_gns3()
    
    # Extract all required links from intent
    required_links = []
    
    # Extract links from "links" array in intent
    for link_def in intent.get('links', []):
        link_name = link_def.get('name', '')
        link_type = link_def.get('type', '')
        endpoints = link_def.get('endpoints', [])
        
        if len(endpoints) >= 2:
            r1 = endpoints[0].get('router', '')
            iface1_full = endpoints[0].get('interface', '')
            r2 = endpoints[1].get('router', '')
            iface2_full = endpoints[1].get('interface', '')
            
            # Extract interface shorthand (g1/0, g2/0, f0/0)
            if '/' in iface1_full:
                iface1_short = 'g' + iface1_full.split('/')[-2][-1] + '/0'
            else:
                iface1_short = iface1_full
                
            if '/' in iface2_full:
                iface2_short = 'g' + iface2_full.split('/')[-2][-1] + '/0'
            else:
                iface2_short = iface2_full
            
            if r1 and r2 and iface1_full and iface2_full:
                link_type_display = 'eBGP' if 'inter' in link_type else 'OSPF/Core'
                required_links.append((r1, iface1_short, r2, iface2_short, link_name, link_type_display))
                print(f"Found {link_type_display} link: {link_name} ({r1} {iface1_short} <-> {r2} {iface2_short})")
    
    print(f"\nTotal links in intent.json: {len(required_links)}")
    
    # Now sync with GNS3
    added_count = 0
    for r1, iface1, r2, iface2, link_name, link_type in required_links:
        uuid1 = ROUTER_UUIDS.get(r1)
        uuid2 = ROUTER_UUIDS.get(r2)
        
        if not uuid1 or not uuid2:
            print(f"  ⚠ SKIP: {link_name} - Router not found in UUID mapping")
            continue
        
        # Check if link exists
        if link_exists(gns3, uuid1, uuid2):
            print(f"  ✓ EXISTS: {link_name} ({r1}<->{r2})")
        else:
            # Create new link
            adapter1 = get_adapter_number(r1, iface1)
            adapter2 = get_adapter_number(r2, iface2)
            
            new_link = create_gns3_link(uuid1, adapter1, uuid2, adapter2, iface1, iface2)
            gns3['topology']['links'].append(new_link)
            added_count += 1
            print(f"  ✅ ADDED: {link_name} ({r1} adapter {adapter1} <-> {r2} adapter {adapter2})")
    
    if added_count > 0:
        print(f"\n✅ Added {added_count} link(s) to GNS3 file")
        save_gns3(gns3)
        print("Saved BIG_automatique.gns3")
    else:
        print("\n👍 All links already exist in GNS3 file")

if __name__ == '__main__':
    main()
