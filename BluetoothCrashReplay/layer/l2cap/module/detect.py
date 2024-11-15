import subprocess


def log_pkt(pkt):
	"""
	get default format of each packet and update the values
	"""
	pkt_default = dict(pkt.default_fields, **pkt.payload.default_fields)
	pkt_default = dict(pkt_default, **pkt.payload.payload.default_fields)
	pkt_CmdHdr_updated = dict(pkt_default, **pkt.fields)
	pkt_payload_updated = dict(pkt_CmdHdr_updated, **pkt.payload.fields)
	pkt_garbage_updated = dict(pkt_payload_updated, ** pkt.payload.payload.fields)
	
	return pkt_garbage_updated


def l2ping(bt_addr):
	"""
	<Crash finding example>
	1) Check the status of sockect in send() method
	2) If there is error in send(), Check l2ping
	3) if l2ping finds packet lost, it is crash!
	+ You need to check the target device's condition. (Error pop-up or crash dump.)
	"""
	l2pingRes = subprocess.run(['l2ping',str(bt_addr),"-c","3"],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	try:
		failureRate = str(l2pingRes.stdout).split()[-2]
		failureRate = int(failureRate.split("%")[0])
	except ValueError:
		failureRate = 100
	if(failureRate < 100):
		return True
	else:
		return False
