import socket
import re
import time
import json
import subprocess as sp
import snap_plugin.v1 as snap


class StorcliCollector(snap.Collector):

    def __init__(self, *args):
        super(StorcliCollector, self).__init__(*args)

    def update_catalog(self, config):
        metrics = []
        metric = snap.Metric(version=1)
        metric.namespace.add_static_element("mfms")                              # /0
        metric.namespace.add_static_element("storcli")                           # /1
        # dynamic elements which are captured from the smartmontool
        metric.namespace.add_dynamic_element("path", "device path")              # /2
        metric.namespace.add_static_element("health")                            # /3
        metrics.append(metric)

        return metrics


    def collect(self, metrics):
        metrics_return = []
        prog = metrics[0].config['storcli_path']
        sudo = metrics[0].config['sudo']
        disks = self.get_storcli_output(prog, sudo)
        for disk in disks:
            metric = snap.Metric(namespace=[i for i in metrics[0].namespace])
            metric.namespace[2].value = disk['Path']
            metric.data = 0 if (disk['State'] == 'JBOD' or disk['State'] == 'Onln') else 1
            metric.timestamp = time.time()
            metric.tags['serialnum'] = disk['SN']
            metrics_return.append(metric)

        return metrics_return

    def get_config_policy(self):
        return snap.ConfigPolicy()

    def get_storcli_output(selfself, prog = 'storcli', sudo=False):
        procs = []
        disks = []
        if sudo:
            procs.append(sp.Popen(['sudo', prog, '/call', '/sall', 'show', 'all', 'J'], stdout=sp.PIPE)) #TODO: check prog availability
            procs.append(sp.Popen(['sudo', prog, '/call', '/eall', '/sall', 'show', 'all', 'J'], stdout=sp.PIPE))
        else:
            procs.append(sp.Popen([prog, '/call', '/sall', 'show', 'all', 'J'], stdout=sp.PIPE))
            procs.append(sp.Popen([prog, '/call', '/eall', '/sall', 'show', 'all', 'J'], stdout=sp.PIPE))

        for proc in procs:
            obj = json.loads(proc.stdout.read())
            for cont in obj['Controllers']:
                if 'Response Data' in cont:
                    dnames =  [name.lstrip('Drive ') for name in cont['Response Data'] if name.find('Detailed Information') < 1]
                    for dname in dnames:
                        info = cont['Response Data']['Drive ' + dname][0]
                        detinfo = cont['Response Data']['Drive ' + dname + ' - Detailed Information']
                        disks.append({
                            'State': info['State'].strip(),
                            'SN': detinfo['Drive ' + dname + ' Device attributes']['SN'].strip(),
                            'Path': info['EID:Slt'].strip(),
                            'Model': info['Model'].strip()
                        })

        return disks
