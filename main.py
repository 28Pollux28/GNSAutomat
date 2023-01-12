import json
import os

from models import Router, Interface, Igp, Neighbor, Network, AdjRib

from jinja2 import Environment, FileSystemLoader

def handle_network(network):
    
     #{'1':{'2':'addresse1','4':'addresse2'},'2':{'1': 'addresse1', '3':"addresse3"}}
    ASList = {}
    for As in network['AS']:
        routerAsList = {}
        ipNetworkUsed = {}
        lastSubnetId = 0
        for router in As['routers']:


            routerObj = Router()
            routerObj.id = router['id']
            routerObj.hostname = As['baseHostname']+router['id']
            intLoopback = Interface()
            intLoopback.name = 'Loopback0'
            intLoopback.add = As['IpLoopbackRange']['start']+hex(int(router['id']))[2:]+"::"+hex(int(router['id']))[2:]
            intLoopback.prefix = As['IpLoopbackRange']['prefix']
            if As['igp']['type'] == 'ospf':
                intLoopback.ospf = True
                intLoopback.ospfArea = "0"
                intLoopback.ospfCost = "0"
            elif As['igp']['type'] == 'rip':
                intLoopback.rip = True
            routerObj.loopback = intLoopback


            routerObj.interfaces = []
            for connection in router['connections']:
                inter = Interface()
                inter.name = "GigabitEthernet"+connection['interface']+"/0"
                if router['id'] in ipNetworkUsed:
                    if connection['router'] in ipNetworkUsed[router['id']]:
                        inter.add = ipNetworkUsed[router['id']][connection['router']]+str(hex(int(router['id']))[2:])
                        inter.prefix = As['IpRange']['prefix']
                    else:
                        lastSubnetId += 1
                        adresse = As['IpRange']['start']+str(hex(lastSubnetId)[2:])+"::"
                        ipNetworkUsed[router['id']][connection['router']] = adresse
                        if connection['router'] not in ipNetworkUsed:
                            ipNetworkUsed[connection['router']] = {}
                        ipNetworkUsed[connection['router']][router['id']] = adresse
                        inter.add = adresse + str(hex(int(router['id']))[2:])
                        inter.prefix = As['IpRange']['prefix']
                else:
                    lastSubnetId += 1
                    adresse = As['IpRange']['start'] + str(hex(lastSubnetId)[2:]) + "::"
                    ipNetworkUsed[router['id']] = {}
                    ipNetworkUsed[router['id']][connection['router']] = adresse
                    if connection['router'] not in ipNetworkUsed:
                        ipNetworkUsed[connection['router']] = {}
                    ipNetworkUsed[connection['router']][router['id']] = adresse
                    inter.add = adresse + str(hex(int(router['id']))[2:])
                    inter.prefix = As['IpRange']['prefix']
                if As['igp']['type'] == 'ospf':
                    inter.ospf=True
                    inter.ospfArea = connection['ospfArea']
                    inter.ospfCost = connection['ospfCost']
                elif As['igp']['type'] == 'rip':
                    inter.rip= True


                routerObj.interfaces.append(inter)


            if(As['igp']['type'] == 'ospf'):
                ospf = Igp()
                ospf.process = router['id']
                ospf.routerId = As['igp']['routerID']+router['id']
                ospf.passiveInterfaces = []
                routerObj.ospf = ospf
            elif(As['igp']['type'] == 'rip'):
                rip = Igp()
                rip.process = routerObj.hostname
                rip.passiveInterfaces = []
                routerObj.rip = rip

            bgp = Igp()
            bgp.as_number = As['number']
            bgp.routerId = As['bgp']['routerID']+router['id']
            bgp.out = AdjRib()
            bgp.out.network = router['bgp']['out']['networks']
            bgp.in_ = AdjRib()
            bgp.neighbors = []
            for routeur in As['routers']:
                # print(routeur['id'], router['id'])
                if routeur['id'] != router['id']:
                    neighbor = Neighbor()
                    neighbor.remote_as = As['number']
                    neighbor.ipAdd = As['IpLoopbackRange']['start']+hex(int(routeur['id']))[2:]+"::"+hex(int(routeur['id']))[2:]
                    bgp.neighbors.append(neighbor)
            routerObj.bgp = bgp



            routerAsList[routerObj.id] = routerObj

        for routeur in routerAsList.values():
            routeur.bgp.networks = []
            if routeur.bgp.out.network == "as":
                for i in range(1,lastSubnetId+1):
                    network2 = Network()
                    network2.add =As['IpRange']['start']+str(hex(i)[2:])+"::"
                    network2.prefix = As['IpRange']['prefix']
                    routeur.bgp.networks.append(network2)
        ASList[As['number']] = routerAsList
    IpRangeLink = 0
    as_link_ = network['ASLink']
    for link in as_link_['links']:
        IpRangeLink += 1
        int1 = Interface()
        int2 = Interface()
        int1.name = "GigabitEthernet"+link['firstInterface']['id']+"/0"
        int2.name = "GigabitEthernet"+link['secondInterface']['id']+"/0"
        add1 = network['ASLink']['IpRange']['start'] + str(hex(IpRangeLink)[2:]) + "::" + str(
            hex(int(link['firstAS']))[2:]) + ":"+str(hex(int(link['firstRouter']))[2:])
        int1.add = add1
        add2 = network['ASLink']['IpRange']['start'] + str(hex(IpRangeLink)[2:]) + "::" + str(
            hex(int(link['secondAS']))[2:]) +":"+ str(hex(int(link['secondRouter']))[2:])
        int2.add = add2
        int1.prefix = network['ASLink']['IpRange']['prefix']
        int2.prefix = network['ASLink']['IpRange']['prefix']
        ASList[link['firstAS']][link['firstRouter']].interfaces.append(int1)
        ASList[link['secondAS']][link['secondRouter']].interfaces.append(int2)
        if hasattr(ASList[link['firstAS']][link['firstRouter']], "ospf"):
            print("ospf", link['firstAS'], link['firstRouter'])
            int1.ospf = True
            int1.ospfArea = link['firstInterface']['ospfArea']
            int1.ospfCost = link['firstInterface']['ospfCost']

            ASList[link['firstAS']][link['firstRouter']].ospf.passiveInterfaces.append(int1.name)
        elif hasattr(ASList[link['firstAS']][link['firstRouter']],"rip"):
            int1.rip = True
            ASList[link['firstAS']][link['firstRouter']].rip.passiveInterfaces.append(int1.name)
        if hasattr(ASList[link['secondAS']][link['secondRouter']], "ospf"):
            int2.ospf = True
            int2.ospfArea = link['secondInterface']['ospfArea']
            int2.ospfCost = link['secondInterface']['ospfCost']

            ASList[link['secondAS']][link['secondRouter']].ospf.passiveInterfaces.append(int2.name)
        elif hasattr(ASList[link['secondAS']][link['secondRouter']], "rip"):
            int2.rip = True
            ASList[link['secondAS']][link['secondRouter']].rip.passiveInterfaces.append(int2.name)
        neighb1 = Neighbor()
        neighb1.remote_as = link['firstAS']
        neighb1.ipAdd = add1
        neighb1.noLoopback = True
        neighb2 = Neighbor()
        neighb2.remote_as = link['secondAS']
        neighb2.ipAdd = add2
        neighb2.noLoopback = True
        ASList[link['firstAS']][link['firstRouter']].bgp.neighbors.append(neighb2)
        ASList[link['secondAS']][link['secondRouter']].bgp.neighbors.append(neighb1)

    return ASList









if __name__ == '__main__':
    environment = Environment(loader=FileSystemLoader('templates/'), trim_blocks = True, lstrip_blocks = True)
    template = environment.get_template('config_template.txt')
    f = open('network.json','r')
    load = json.load(f)
    ASList = handle_network(load)
    for AS in ASList.values():
        for router in AS.values():
            print(router.hostname)
            path = "C:/Users/lemai/GNS3/projects/ProjetGNS3/project-files/dynamips"
            cfg_file = 'i' + str(load['routerMap'][router.hostname]) + "_startup-config.cfg"
            real_path=""
            for root, dirs, files in os.walk(path):
                if cfg_file in files:
                    real_path = os.path.join(root, cfg_file)
            f2 = open(real_path, "w")
            f2.write(template.render(router=router))
            f2.close()
    # print(template.render(router=ASList['200']['7']))
    f.close()






    # router = {
    #     'hostname': 'R1111',
    #     'loopback': {
    #         'name': 'Loopback0',
    #         'ipv6Address:
    #             {
    #                 'add': "FE01:1:1::1",
    #                 'prefix': 64
    #             }
    #
    #         'rip': True,
    #     },
    #     'interfaces': [
    #         {
    #             'name': 'GigabitEthernet1/0',
    #             'ipv6Addresses': [
    #                 {
    #                     'add': "2020:100:1:1::1",
    #                     'prefix': 64
    #                 },
    #             ],
    #             'rip': True,
    #
    #         },
    #         {
    #             'name': 'GigabitEthernet2/0',
    #             'ipv6Addresses': [
    #                 {
    #                     'add': "2020:100:1:2::1",
    #                     'prefix': 64
    #                 },
    #             ],
    #             'rip': True,
    #
    #         },
    #     ],
    #     'rip': {
    #         "process": "R1111",
    #     },
    #     'bgp': {
    #         'as_number': 100,
    #         'neighbors': [
    #             {
    #                 'ipAdd': 'FE01:1:2::2',
    #                 'remote_as': 100,
    #             },
    #             {
    #                 'ipAdd': 'FE01:1:3::3',
    #                 'remote_as': 100,
    #             },
    #             {
    #                 'ipAdd': 'FE01:1:4::4',
    #                 'remote_as': 100,
    #             },
    #             {
    #                 'ipAdd': 'FE01:1:5::5',
    #                 'remote_as': 100,
    #             },
    #             {
    #                 'ipAdd': 'FE01:1:6::6',
    #                 'remote_as': 100,
    #             },
    #             {
    #                 'ipAdd': 'FE01:1:7::7',
    #                 'remote_as': 100,
    #             },
    #         ],
    #     },
    #
    # }
    #
    # print(template.render(router = router))
