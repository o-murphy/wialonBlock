import logging
from typing import Dict, Any, List, Tuple

from aiowialon import Wialon
from dataclasses import dataclass, field


class WialonSession(Wialon):

    async def __aenter__(self):
        """
        Asynchronously enters the context, performing Wialon login.
        """
        logging.info(f"Attempting Wialon login for host: {self.host}...")
        # Use the stored token and app_name for login
        try:
            await self.login()
            logging.info(f"Successfully logged in to Wialon for host: {self.host}")
        except Exception as e:
            logging.error(f"Failed to log in to Wialon for host {self.host}: {e}")
            # Re-raise the exception to propagate login failure
            raise
        return self  # Important: return self so 'as session' works

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Asynchronously exits the context, performing Wialon logout.
        Logs any exceptions that occurred within the 'async with' block.
        """
        logging.info(f"Attempting Wialon logout for host: {self.host}...")
        try:
            await self.logout()
            logging.info(f"Successfully logged out from Wialon for host: {self.host}")
        except Exception as e:
            logging.error(f"Error during Wialon logout for host {self.host}: {e}")
        # If exc_type is not None, an exception occurred in the 'async with' block.
        # By not returning True, the exception will be re-raised after __aexit__.
        if exc_type:
            logging.error(f"An exception of type {exc_type.__name__} occurred: {exc_val}")


@dataclass
class Worker:
    wln_host: str
    tg_groups: Dict[str, Dict[str, Any]]

    async def get_group_objects(self, group_name, session: WialonSession):
        params = {
            "spec": {
                "itemsType": "avl_unit_group",
                # "itemsType": "avl_unit",
                "propName": "sys_name",
                # "propValueMask": "*",
                "propValueMask": group_name,
                "sortType": "sys_name",
                "propType": ""
            },
            "force": 1,
            "flags": 5,
            "from": 0,
            # "to": 0
            "to": 1
        }
        response = await session.core_search_items(**params)
        items = response.get('items', [])
        if not items:
            return []
        return items[0].get('u', [])

    async def get_objects(self, *ids, session: WialonSession):
        if not ids:
            return []
        params = {
            "spec": {
                "itemsType": "avl_unit",
                "propName": "sys_id",
                # "propValueMask": "*",
                "propValueMask": "|".join([str(i) for i in ids]),
                "sortType": "sys_name",
                "propType": ""
            },
            "force": 1,
            "flags": 5,
            "from": 0,
            "to": len(ids)
        }
        response = await session.core_search_items(**params)
        items = response.get('items', [])
        return items


    async def list_by_tg_group_id(self, group_id) -> Dict[str, Any]:
        if group := self.tg_groups.get(str(group_id), None):
            async with WialonSession(token=group['wln_token'], host=self.wln_host) as session:
                locked = group['wln_group_locked']
                unlocked = group['wln_group_unlocked']
                ignored = group['wln_group_ignored']
                uids = await self.get_group_objects("|".join([locked, unlocked]), session)
                if ignored:
                    ignored_uids = await self.get_group_objects(ignored, session)
                else:
                    ignored_uids = []
                uids = set(uids) - set(ignored_uids)
                objects = await self.get_objects(*uids, session=session)
                return objects
        else:
            raise Exception(f"Group ID {group_id} not found.")

    async def lock_by_wln_uid(self, uid):
        ...

    async def unlock_by_wln_uid(self, uid):
        ...