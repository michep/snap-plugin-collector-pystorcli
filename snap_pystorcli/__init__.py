import socket
import time
import json
import os
import sys
import snap_plugin.v1 as snap

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as sp
else:
    import subprocess as sp

class StorcliCollector(snap.Collector):

    def __init__(self, *args):
        self.hostname = socket.gethostname().lower()
        super(StorcliCollector, self).__init__(*args)

    def update_catalog(self, config):
        metrics = []
        metric = snap.Metric(version=1)
        metric.namespace.add_static_element("mfms")                              # /0
        metric.namespace.add_static_element("storcli")                           # /1
        metric.namespace.add_dynamic_element("path", "device path")              # /2
        metric.namespace.add_static_element("health")                            # /3
        metrics.append(metric)

        return metrics


    def collect(self, metrics):
        metrics_return = []
        ts_now = time.time()
        prog = metrics[0].config['storcli_path']
        sudo = metrics[0].config['sudo']
        disks = self.get_storcli_output(prog, sudo)
        for disk in disks:
            metric = snap.Metric(namespace=[i for i in metrics[0].namespace])
            metric.namespace[2].value = disk['Path']
            metric.data = 0 if disk['State'] in ('JBOD', 'Onln', 'GHS') else 1
            metric.timestamp = ts_now
            metric.tags['serialnum'] = disk['SN']
            metrics_return.append(metric)

        return metrics_return

    def get_config_policy(self):
        return snap.ConfigPolicy([
            ("mfms", "storcli"),
            [
                (
                    "storcli_path",
                    snap.StringRule(required=True, default="storcli")
                ),
                (
                    "sudo",
                    snap.BoolRule(required=True)
                )
            ]
        ])

    def get_storcli_output(selfself, prog, sudo):
        procs = []
        disks = []
        if sudo:
            procs.append(sp.Popen(['sudo', prog, '/call', '/sall', 'show', 'all', 'J'], stdout=sp.PIPE)) #TODO: check prog availability
            procs.append(sp.Popen(['sudo', prog, '/call', '/eall', '/sall', 'show', 'all', 'J'], stdout=sp.PIPE))
        else:
            procs.append(sp.Popen([prog, '/call', '/sall', 'show', 'all', 'J'], stdout=sp.PIPE))
            procs.append(sp.Popen([prog, '/call', '/eall', '/sall', 'show', 'all', 'J'], stdout=sp.PIPE))

        for proc in procs:
            try:
                stdout, stderr = proc.communicate(timeout=120)
            except sp.TimeoutExpired:
                proc.kill()
                continue

            if stdout == "":
                continue

            obj = json.loads(stdout)
            for cont in obj['Controllers']:
                if 'Response Data' in cont:
                    dnames =  [name.lstrip('Drive ') for name in cont['Response Data'] if name.find('Information') < 0]
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
