import json
import os

from models import Router, Interface, Igp, Neighbor, Network, AdjRib, RouteMap, AsPathAccessList, PrefixList

from jinja2 import Environment, FileSystemLoader

def handle_network(network):
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
        neighb1.routeMapIns = []
        neighb1.routeMapOuts = []
        ASList[link['firstAS']][link['firstRouter']].routeMapIns = []
        ASList[link['firstAS']][link['firstRouter']].routeMapOuts = []
        neighb2 = Neighbor()
        neighb2.remote_as = link['secondAS']
        neighb2.ipAdd = add2
        neighb2.noLoopback = True
        neighb2.routeMapIns = []
        neighb2.routeMapOuts = []
        ASList[link['secondAS']][link['secondRouter']].routeMapIns = []
        ASList[link['secondAS']][link['secondRouter']].routeMapOuts = []
        match link['relationship']:
            case "business":
                print("test")
                neighb2.routeMapIn = "mapLocPrefClient"

                routeMapIn = RouteMap()
                routeMapIn.name = "mapLocPrefClient"
                routeMapIn.action = "permit"
                routeMapIn.sequence = 10
                routeMapIn.match = "as-path"
                routeMapIn.asPathAccessList = str(link['secondAS'])
                routeMapIn.sets= []
                routeMapIn.sets.append("local-preference 250")
                ASList[link['firstAS']][link['firstRouter']].routeMapIns.append(routeMapIn)
                ASList[link['firstAS']][link['firstRouter']].asPathAccessLists = []
                asPathAccessList = AsPathAccessList()
                asPathAccessList.name = str(link['secondAS'])
                asPathAccessList.action = "permit"
                asPathAccessList.as_path = "_"+str(link['secondAS'])+"_"
                ASList[link['firstAS']][link['firstRouter']].asPathAccessLists.append(asPathAccessList)
                neighb2.routeMapIns.append("mapLocPrefClient")


        fil1 = link['filter1']
        fil1In = fil1['in']
        fil1Out = fil1['out']
        ASList[link['firstAS']][link['firstRouter']].prefixLists = []

        fil2 = link['filter2']
        fil2In = fil2['in']
        fil2Out = fil2['out']
        ASList[link['secondAS']][link['secondRouter']].prefixLists = []

        prefixList = PrefixList()
        prefixList.name = "prefixListIn"
        prefixList.action = "permit"
        prefixList.prefixes = []
        for prefix in fil1In['prefixes']:
             prefixList.prefixes.append(prefix)
        if len(prefixList.prefixes) > 0:
            ASList[link['firstAS']][link['firstRouter']].prefixLists.append(prefixList)
            routeMapFilter1In = RouteMap()
            routeMapFilter1In.name = "routeMapFilter1In"
            routeMapFilter1In.action = "deny"
            routeMapFilter1In.sequence = 10
            routeMapFilter1In.match = "ipv6 address"
            routeMapFilter1In.ipv6AccessList = "prefixListIn"
            ASList[link['firstAS']][link['firstRouter']].routeMapIns.append(routeMapFilter1In)
            neighb2.routeMapIns.append("routeMapFilter1In")

        prefixList = PrefixList()
        prefixList.name = "prefixListOut"
        prefixList.action = "permit"
        prefixList.prefixes = []
        for prefix in fil1Out['prefixes']:
            prefixList.prefixes.append(prefix)
        if len(prefixList.prefixes) > 0:
            ASList[link['firstAS']][link['firstRouter']].prefixLists.append(prefixList)
            routeMapFilter1Out = RouteMap()
            routeMapFilter1Out.name = "routeMapFilter1Out"
            routeMapFilter1Out.action = "deny"
            routeMapFilter1Out.sequence = 10
            routeMapFilter1Out.match = "ipv6 address"
            routeMapFilter1Out.ipv6AccessList = "prefixListOut"
            ASList[link['firstAS']][link['firstRouter']].routeMapOuts.append(routeMapFilter1Out)
            neighb2.routeMapOuts.append("routeMapFilter1Out")

        prefixList = PrefixList()
        prefixList.name = "prefixListIn"
        prefixList.action = "permit"
        prefixList.prefixes = []
        for prefix in fil2In['prefixes']:
             prefixList.prefixes.append(prefix)
        if(len(prefixList.prefixes) > 0):
            ASList[link['secondAS']][link['secondRouter']].prefixLists.append(prefixList)
            routeMapFilter2In = RouteMap()
            routeMapFilter2In.name = "routeMapFilter2In"
            routeMapFilter2In.action = "deny"
            routeMapFilter2In.sequence = 10
            routeMapFilter2In.match = "ipv6 address"
            routeMapFilter2In.ipv6AccessList = "prefixListIn"
            ASList[link['secondAS']][link['secondRouter']].routeMapIns.append(routeMapFilter2In)
            neighb1.routeMapIns.append("routeMapFilter2In")

        prefixList = PrefixList()
        prefixList.name = "prefixListOut"
        prefixList.action = "permit"
        prefixList.prefixes = []
        for prefix in fil2Out['prefixes']:
            prefixList.prefixes.append(prefix)
        if(len(prefixList.prefixes) > 0):
            ASList[link['secondAS']][link['secondRouter']].prefixLists.append(prefixList)
            routeMapFilter2Out = RouteMap()
            routeMapFilter2Out.name = "routeMapFilter2Out"
            routeMapFilter2Out.action = "deny"
            routeMapFilter2Out.sequence = 10
            routeMapFilter2Out.match = "ipv6 address"
            routeMapFilter2Out.ipv6AccessList = "prefixListOut"
            ASList[link['secondAS']][link['secondRouter']].routeMapOuts.append(routeMapFilter2Out)
            neighb1.routeMapOuts.append("routeMapFilter2Out")


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
    f.close()
