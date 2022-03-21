from pymongo import MongoClient
from flask import Flask, request, Response
import os
import json
import pymongo
from vk_worker import VkWorker
import logging

client = MongoClient(os.environ["MONGO_URL"])

app = Flask(__name__)

db = client.scrape_db

communities = db.communities

worker = VkWorker(communities, os.environ["VK_TOKEN"])

worker.start()


@app.route("/<group_id>", methods=["GET", "POST"])
def fetch_group(group_id):

    existing = communities.find_one({"_id": group_id})

    if request.method == "POST":
        worker.enque(group_id, force=True)
        return "enqued", 202
    else:
        if existing is None:
            return "null"
        else:
            return json.dumps(existing)


@app.route("/fetch", methods=["POST"])
def long_fetch():
    groups = request.get_json(force=True)
    for group in groups:
        worker.enque(group)
    return ""


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    app.run(host='0.0.0.0', port=80)
