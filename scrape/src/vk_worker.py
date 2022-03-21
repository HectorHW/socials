from typing import Union
from dataclasses import dataclass
from queue import Queue
import vk_api
import threading
import pymongo
import sys
import time
from string import Template
import logging
from timeit import default_timer as timer
from datetime import timedelta


@dataclass
class QueueEntry:
    id: Union[str, int]
    force: bool = False


POLL_SIZE = 25000

LOGGER = logging.getLogger("vk_worker")
LOGGER.addHandler(logging.StreamHandler(sys.stdout))
LOGGER.setLevel("INFO")


class VkWorker:
    def __init__(self, communities_collection, token) -> None:
        self._queue: Queue[QueueEntry] = Queue()
        self._vk_session = vk_api.VkApi(token=token)
        self._vk = self._vk_session.get_api()
        self._worker = None
        self._communities = communities_collection
        with open('poll_group.script') as poll:
            self.template = Template(poll.read())

    def start(self):
        if self._worker is not None:
            raise ValueError

        self._worker = threading.Thread(target=self._worker_method)
        self._worker.daemon = True
        self._worker.start()

    def enque(self, group_id, force: bool = False):
        self._queue.put(QueueEntry(group_id, force))

    def _scrape_community(self):
        pass

    def _worker_method(self):
        while True:
            entry = self._queue.get(block=True)
            LOGGER.info(f'picked up {entry.id}')
            time.sleep(0.1)

            try:

                if isinstance(entry.id, str):
                    group_name = entry.id.strip('/').split('/')[-1]
                else:
                    group_name = entry.id

                group_info = self._vk.groups.getById(
                    group_id=group_name)[0]
                time.sleep(0.1)
                entry.id = group_info['id']

                members = []
                offset = 0

                if not entry.force and self._communities.find_one({"_id": entry.id}) is not None:
                    LOGGER.warn(
                        f"duplicate {entry.id} ({group_info['name']}), skipping")
                    continue

                start_time = timer()

                while True:
                    try:
                        resp = self._vk.execute(code=self.template.substitute(
                            {
                                "group_id": str(entry.id),
                                "offset": str(offset)
                            }
                        ))

                        members += resp
                        if len(resp) < POLL_SIZE:
                            break
                        offset += POLL_SIZE
                    except vk_api.exceptions.ApiError:
                        time.sleep(0.1)

                end_time = timer()

                LOGGER.info(
                    f"pulled {len(members)} records in {timedelta(seconds=end_time-start_time)}")

                self._communities.insert_one({
                    "_id": entry.id,
                    "name": group_info["name"],
                    "size": len(members),
                    "users": members,
                    "tags": []
                })

            except pymongo.errors.DuplicateKeyError:
                pass

            except vk_api.exceptions.ApiError as e:
                LOGGER.error(e)
