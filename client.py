
import base64
import json
import logging
import requests
import secrets
import socket
import subprocess
import threading
import time

import flask
import zeroconf


logging.basicConfig(filename='vsnm.log', encoding='utf-8', level=logging.WARNING)


def get_local_ip():
	local_ip = None
	while not local_ip:
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.connect(("8.8.8.8", 80))
			local_ip = s.getsockname()[0]
			s.close()
		except OSError:
			time.sleep(3)
	return local_ip


def ping(addr):
	try:
		output = subprocess.check_output(['ping', '-c', '1', addr])
	except subprocess.CalledProcessError:
		logging.debug('Ping %s returned non-zero.' % addr)
		return -1
	output = output.decode("utf-8")
	logging.debug('Ping to %s output: %s' % (addr, output))
	return float(output.split('/')[-3])


LOCAL_IP = get_local_ip()
SERVICE_TYPE = "_vsnm._tcp.local."
SERVICE_NAME = "%s.%s" % (LOCAL_IP, SERVICE_TYPE)
SERVICE_PORT = 1048
POLL_REMOTES = [
	"google.com",
	"justingiorgi.com",
	"apple.com",
]
POLL_LOCALS = {}

API_BASE = "http://justingiorgi.com:1048"

FREQ_PING = 5  # 5 seconds
FREQ_UPLOAD = 60  # 1 minute
FREQ_SPEEDTEST = 900  # 15 minutes

SPEEDTEST_SIZE = 2 * 1000 * 1000  # 2 Mebibits


class Listener:

	def __init__(self, mdns_r):
		self.mdns_r = mdns_r

	def remove_service(self, zeroconf, s_type, name):
		logging.debug('Got stop service %s' % name)
		if name in POLL_LOCALS:
			logging.debug('Removed service %s from local pollers.' % name)
			del POLL_LOCALS[name]

	def add_service(self, zeroconf, s_type, name):
		print('Got add service %s' % name)
		if name == SERVICE_NAME:
			print('Service is us, ignoring.')
			return
		info = self.mdns_r.get_service_info(s_type, name)
		addr = info.parsed_addresses()[0]
		logging.debug('Adding local poller name %s with addr %s' % (name, addr))
		POLL_LOCALS[name] = addr

	def update_service(self, zeroconf, s_type, name):
		self.add_service(zeroconf, s_type, name)


app = flask.Flask(__name__)

@app.route("/junk", methods=["GET"])
def get_junk():
    junk_bytes = secrets.token_bytes(SPEEDTEST_SIZE)
    return base64.b64encode(junk_bytes)


@app.route("/junk", methods=["POST"])
def post_junk():
	data = flask.request.get_json()
	return 'Success'


def main():
	logging.debug('Starting flask in thread.')
	threading.Thread(target=lambda: app.run(host=LOCAL_IP, port=SERVICE_PORT, debug=True, use_reloader=False)).start()

	logging.debug('Starting zeroconf service broadcast.')
	mdns_r = zeroconf.Zeroconf()
	info = zeroconf.ServiceInfo(
		SERVICE_TYPE,
		SERVICE_NAME,
		addresses=[LOCAL_IP],
		port=SERVICE_PORT)
	mdns_r.register_service(info)

	logging.debug('Starting zeroconf service listener.')
	listener = Listener(mdns_r)
	browser = zeroconf.ServiceBrowser(mdns_r, SERVICE_TYPE, listener=listener)

	print('Starting poller loop.')
	response_cache = {}
	last_upload = 0
	last_speedtest = 0
	last_ping = 0
	while True:

		if time.time() < last_ping + FREQ_PING:
			time.sleep((last_ping + FREQ_PING) - time.time())

		# Ping loop.
		responses = {}
		for addr in POLL_REMOTES + list(POLL_LOCALS.values()):
			responses[addr] = ping(addr)
		response_cache[time.time()] = responses
		last_ping = time.time()

		# Upload
		if time.time() - last_upload >= FREQ_UPLOAD:
			print('Uploading cache')
			try:
				requests.post(API_BASE + '/data', data=json.dumps({'name': SERVICE_NAME, 'data': response_cache}))
			except requests.RequestException as e:
				logging.error(e, exc_info=True)
			last_upload = time.time()

		# Speed test
		if time.time() - last_speedtest >= FREQ_SPEEDTEST:
			print('Running speedtests')
			speedtests = {}
			for local_ip in list(POLL_LOCALS.values()) + ["justingiorgi.com"]:
				try:
					dl_start = time.time()
					req = requests.get("http://" + local_ip + ":1048/junk")
					junk = req.text
					dl_end = time.time()
					requests.post("http://" + local_ip + ":1048/junk", data=json.dumps({"junk": junk}))
					ul_end = time.time()
				except requests.RequestException as e:
					logging.error(e, exc_info=True)
					dl_time = -1
					ul_time = -1
				else:
					dl_time = dl_end - dl_start
					ul_time = ul_end - dl_end
				speedtests[local_ip] = {"dl_time": dl_time, "ul_time": ul_time}
			try:
				requests.post(API_BASE + "/speedtest", data=json.dumps({"name": SERVICE_NAME, "time": time.time(), "data": speedtests}))
			except requests.RequestException as e:
				logging.error(e, exc_info=True)
			else:
				last_speedtest = time.time()
	

if __name__ == "__main__":
	while True:
		try:
			main()
		except KeyboardInterrupt:
			logging.debug('Got keyboard interrupt, exiting.')
			break
		except Exception as e:
			logging.error(e, exc_info=True)
