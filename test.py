import snap_pystorcli



coll  = snap_pystorcli.StorcliCollector()
devs = coll.get_storcli_output()
print(json.dumps(devs))

