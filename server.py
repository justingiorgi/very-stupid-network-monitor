import base64
import json
import secrets

import flask
import pymongo


SPEEDTEST_SIZE = 2 * 1000 * 1000  # 2 Mebibits


app = flask.Flask(__name__)
client = pymongo.MongoClient()
db = client.vsnm


@app.route("/junk", methods=["GET"])
def get_junk():
    junk_bytes = secrets.token_bytes(SPEEDTEST_SIZE)
    return base64.b64encode(junk_bytes)


@app.route("/junk", methods=["POST"])
def post_junk():
	data = json.loads(flask.request.data)
	return 'Success'


@app.route("/data", methods=["POST"])
def post_data():
	data = json.loads(flask.request.data)
	for ts in data["data"].keys():
		hosts = data["data"][ts]
		doc = {
			"name": data["name"],
			"time": ts,
			"hosts": [],
		}
		for host, resp_ms in hosts.items():
			doc["hosts"].append({"host": host, "ms": resp_ms})
		db.pings.insert_one(doc)
	return 'Success'


@app.route("/speedtest", methods=["POST"])
def post_speedtest():
	data = json.loads(flask.request.data)
	doc = {
		"name": data["name"],
		"time": data["time"],
		"hosts": []}
	for k, v in data["data"].items():
		doc["hosts"].append({
			"host": k,
			"ul_time": v["ul_time"],
			"dl_time": v["dl_time"],
			})
	db.speedtests.insert_one(doc)
	return 'Success'


if __name__ == "__main__":
	app.run(host="::", port=1048)
