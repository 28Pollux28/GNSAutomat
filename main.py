import json
from models import Router, Interface, Igp, Neighbor, Network, AdjRib

from jinja2 import Environment, FileSystemLoader

def handle_network(network):
    routerList = []
     #{'1':{'2':'addresse1','4':'addresse2'},'2':{'1': 'addresse1', '3':"addresse3"}}
    for As in network['AS']:
        ipNetworkUsed = {}
        lastSubnetId = 0
        for router in As['routers']:


            routerObj = Router()
            routerObj.hostname = As['baseHostname']+router['id']
            intLoopback = Interface()
            intLoopback.name = 'Loopback0'
            intLoopback.add = As['IpLoopbackRange']['start']+router['id']+"::"+router['id']
            intLoopback.prefix = As['IpLoopbackRange']['prefix']
            routerObj.loopback = intLoopback


            routerObj.interfaces = []
            for connection in router['connections']:
                int = Interface()
                int.name = "GigabitEthernet"+connection['interface']+"/0"
                if router['id'] in ipNetworkUsed:
                    if connection['router'] in ipNetworkUsed[router['id']]:
                        int.add = ipNetworkUsed[router['id']][connection['router']]+str(router['id'])
                        int.prefix = As['IpRange']['prefix']
                    else:
                        lastSubnetId += 1
                        adresse = As['IpRange']['start']+str(lastSubnetId)+"::"
                        ipNetworkUsed[router['id']][connection['router']] = adresse
                        if connection['router'] not in ipNetworkUsed:
                            ipNetworkUsed[connection['router']] = {}
                        ipNetworkUsed[connection['router']][router['id']] = adresse
                        int.add = adresse + str(router['id'])
                        int.prefix = As['IpRange']['prefix']
                else:
                    lastSubnetId += 1
                    adresse = As['IpRange']['start'] + str(lastSubnetId) + "::"
                    ipNetworkUsed[router['id']] = {}
                    ipNetworkUsed[router['id']][connection['router']] = adresse
                    if connection['router'] not in ipNetworkUsed:
                        ipNetworkUsed[connection['router']] = {}
                    ipNetworkUsed[connection['router']][router['id']] = adresse
                    int.add = adresse + str(router['id'])
                    int.prefix = As['IpRange']['prefix']
                if As['igp']['type'] == 'ospf':
                    int.ospf=True
                    int.ospfArea = connection['ospfArea']
                    int.ospfCost = connection['ospfCost']
                elif As['igp']['type'] == 'rip':
                    int.rip= True


                routerObj.interfaces.append(int)


            if(As['igp']['type'] == 'ospf'):
                ospf = Igp()
                ospf.process = router['id']
                ospf.routerId = As['igp']['routerID']+router['id']
                ospf.passiveInterfaces = []
                for interface in router['igp']['passiveInterfaces']:
                    ospf.passiveInterfaces.append("GigabitEthernet"+interface+"/0")
                routerObj.ospf = ospf
            elif(As['igp']['type'] == 'rip'):
                rip = Igp()
                rip.process = routerObj.hostname
                rip.passiveInterfaces = []
                for interface in As['igp']['passiveInterfaces']:
                    rip.passiveInterfaces.append("GigabitEthernet"+interface+"/0")
                routerObj.rip = rip

            bgp = Igp()
            bgp.as_number = As['number']
            bgp.routerId = As['bgp']['routerID']+router['id']
            bgp.out = AdjRib()
            bgp.out.network = router['bgp']['out']['networks']
            bgp.in_ = AdjRib()
            bgp.neighbors = []
            for routeur in As['routers']:
                print(routeur['id'], router['id'])
                if routeur['id'] != router['id']:
                    neighbor = Neighbor()
                    neighbor.remote_as = As['number']
                    neighbor.ipAdd = As['IpLoopbackRange']['start']+routeur['id']+"::"+routeur['id']
                    bgp.neighbors.append(neighbor)
            print(bgp.neighbors)
            routerObj.bgp = bgp



            routerList.append(routerObj)

        for routeur in routerList:
            routeur.bgp.networks = []
            if routeur.bgp.out.network == "as":
                for i in range(1,lastSubnetId+1):
                    network = Network()
                    network.add =As['IpRange']['start']+str(i)+"::"
                    network.prefix = As['IpRange']['prefix']
                    routeur.bgp.networks.append(network)
    return routerList







if __name__ == '__main__':
    environment = Environment(loader=FileSystemLoader('templates/'), trim_blocks = True, lstrip_blocks = True)
    template = environment.get_template('config_template.txt')
    f = open('network.json','r')
    routerList = handle_network(json.load(f))
    print(routerList[0].bgp)
    print(template.render(router=routerList[0]))
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
