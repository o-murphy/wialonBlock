import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, Any, Tuple, Optional, Type

from aiowialon import Wialon
from aiowialon.types import flags
from aiowialon.types.flags import UnitsDataFlag

from wialonblock.config import TelegramGroup


class WialonSession(Wialon):

    @property
    def base_url(self) -> str:
        return self._Wialon__base_url

    async def __aenter__(self):
        """
        Asynchronously enters the context, performing Wialon login.
        """
        logging.info(f"Attempting Wialon login for host: {self.base_url}...")
        # Use the stored token and app_name for login
        try:
            await self.login()
            logging.info(f"Successfully logged in to Wialon for host: {self.base_url}")
        except Exception as e:
            logging.error(f"Failed to log in to Wialon for host {self.base_url}: {e}")
            # Re-raise the exception to propagate login failure
            raise
        return self  # Important: return self so 'as session' works

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Asynchronously exits the context, performing Wialon logout.
        Logs any exceptions that occurred within the 'async with' block.
        """
        logging.info(f"Attempting Wialon logout for host: {self.base_url}...")
        try:
            await self.logout()
            logging.info(f"Successfully logged out from Wialon for host: {self.base_url}")
        except Exception as e:
            logging.error(f"Error during Wialon logout for host {self.base_url}: {e}")
        # If exc_type is not None, an exception occurred in the 'async with' block.
        # By not returning True, the exception will be re-raised after __aexit__.
        if exc_type:
            logging.error(f"An exception of type {exc_type.__name__} occurred: {exc_val}")


class ObjState(StrEnum):
    UNKNOWN = "❓"
    LOCKED = "⛔️"
    UNLOCKED = "🟢"


@dataclass
class WialonWorker:
    wln_host: str
    wln_token: str
    tg_groups: Dict[str, TelegramGroup]
    session: Type[WialonSession] = WialonSession

    async def _get_group_by_name(self, group_name, session: WialonSession):
        params = {
            "spec": {
                "itemsType": "avl_unit_group",
                "propName": "sys_name",
                "propValueMask": group_name,
                "sortType": "sys_name",
                "propType": ""
            },
            "force": 1,
            "flags": UnitsDataFlag.BASE | UnitsDataFlag.BILLING_PROPS,
            "from": 0,
            "to": 0
        }
        response = await session.core_search_items(**params)
        items = response.get('items', [])
        if not items:
            return None
        return items[0]

    async def _get_group_objects(self, *group_names, session: WialonSession):
        params = {
            "spec": {
                "itemsType": "avl_unit_group",
                "propName": "sys_name",
                "propValueMask": "|".join(group_names),
                "sortType": "sys_name",
                "propType": ""
            },
            "force": 1,
            "flags": UnitsDataFlag.BASE | UnitsDataFlag.BILLING_PROPS,
            "from": 0,
            "to": len(group_names)
        }
        response = await session.core_search_items(**params)
        items = response.get('items', [])
        if not items:
            return []
        # join all items
        return [item for each in items for item in each.get('u', [])]

    async def _get_objects_by_ids(self, ids, pattern: str = "", session: WialonSession = None):
        if not ids:
            return []
        ids_mask = "|".join([str(i) for i in ids])

        if not self.has_special_character_loop(pattern):
            pattern = f"*{pattern}*"

        params = {
            "spec": {
                "itemsType": "avl_unit",
                "propName": "sys_id,sys_name",
                # "propValueMask": "*",
                "propValueMask": f"{ids_mask},{pattern}",
                "sortType": "sys_name",
                "propType": ""
            },
            "force": 1,
            "flags": UnitsDataFlag.BASE | UnitsDataFlag.BILLING_PROPS,
            "from": 0,
            "to": 0
        }
        response = await session.core_search_items(**params)
        items = response.get('items', [])
        return items

    async def get_groups(self, tg_group_id) -> Optional[Tuple[TelegramGroup, ...]]:
        if groups := self.tg_groups.get(str(tg_group_id), None):
            return groups.wln_group_locked, groups.wln_group_unlocked, groups.wln_group_ignored
        raise Exception(f"Group `%s` not found." % tg_group_id)

    async def _get_unit(self, uid, session):
        uid = int(uid)
        params = {
            "id": uid,
            "flags": (
                    UnitsDataFlag.BASE
                    | UnitsDataFlag.BILLING_PROPS
                # | UnitsDataFlag.LAST_MSG_N_POS
                # | UnitsDataFlag.POS
                # | UnitsDataFlag.SENSORS
            )
        }
        return await session.core_search_item(**params)

    async def _swap_groups(self, uid, from_group_name, to_group_name, session: WialonSession):
        from_group = await self._get_group_by_name(from_group_name, session=session)
        to_group = await self._get_group_by_name(to_group_name, session=session)
        if not from_group or not to_group:
            raise ValueError("One of the groups not found")
        from_uids = from_group.get('u', [])
        to_uids = to_group.get('u', [])

        if not from_uids and not to_uids:
            raise ValueError("Both groups are empty")

        if not uid in from_uids:
            raise ValueError("Object `%s` not found in expected group `%s`" % (uid, from_group["id"]))

        from_uids.remove(uid)
        to_uids.append(uid)

        update_from_group_call = session.unit_group_update_units(
            **{"itemId": from_group["id"], "units": from_uids}
        )

        update_to_group_call = session.unit_group_update_units(
            **{"itemId": to_group["id"], "units": to_uids}
        )

        await session.batch(
            update_from_group_call,
            update_to_group_call,
            flags_=flags.BatchFlag.STOP_ON_ERROR
        )

    async def lock(self, tg_group_id, uid):
        uid = int(uid)
        group = await self.get_groups(tg_group_id)
        async with WialonSession(token=self.wln_token, host=self.wln_host) as session:
            locked, unlocked, ignored = group
            await self._swap_groups(uid, unlocked, locked, session=session)
            return await self._get_unit_and_lock_state(group, uid, session=session)

    async def unlock(self, tg_group_id, uid):
        uid = int(uid)
        group = await self.get_groups(tg_group_id)
        async with WialonSession(token=self.wln_token, host=self.wln_host) as session:
            locked, unlocked, ignored = group
            await self._swap_groups(uid, locked, unlocked, session=session)
            return await self._get_unit_and_lock_state(group, uid, session=session)

    async def _check_is_locked(self, uid, locked_uids, unlocked_uids):
        if uid in locked_uids and uid in unlocked_uids:
            logging.error("Device in both groups, uid: `%s`" % uid)
            return ObjState.UNKNOWN
        elif uid in locked_uids:
            return ObjState.LOCKED
        elif uid in unlocked_uids:
            return ObjState.UNLOCKED
        logging.error("Not found, uid: `%s`" % uid)
        return ObjState.UNKNOWN

    async def _get_unit_and_lock_state(self, group: Tuple[TelegramGroup, TelegramGroup, TelegramGroup],
                                       uid, session):
        uid = int(uid)
        locked, unlocked, ignored = group
        locked_uids = await self._get_group_objects(locked, session=session)
        unlocked_uids = await self._get_group_objects(unlocked, session=session)
        lock_state = await self._check_is_locked(uid, locked_uids, unlocked_uids)
        unit = await self._get_unit(uid, session=session)
        return unit, lock_state

    async def get_unit_and_lock_state(self, tg_group_id, uid):
        group = await self.get_groups(tg_group_id)
        async with WialonSession(token=self.wln_token, host=self.wln_host) as session:
            return await self._get_unit_and_lock_state(group, uid, session=session)

    @staticmethod
    def has_special_character_loop(input_string):
        special_characters = "*|><=!"
        for char in input_string:
            if char in special_characters:
                return True
        return False

    async def list_by_tg_group_id(self, tg_group_id, pattern: str = "") -> Dict[str, Any]:
        group = await self.get_groups(tg_group_id)
        async with WialonSession(token=self.wln_token, host=self.wln_host) as session:
            locked, unlocked, ignored = group
            locked_uids = await self._get_group_objects(locked, session=session)
            unlocked_uids = await self._get_group_objects(unlocked, session=session)
            uids = locked_uids + unlocked_uids
            if ignored:
                ignored_uids = await self._get_group_objects(ignored, session=session)
            else:
                ignored_uids = []

            uids = set(uids) - set(ignored_uids)
            objects = await self._get_objects_by_ids(uids, pattern=pattern, session=session)
            for obj in objects:
                obj['_lock_'] = await self._check_is_locked(obj['id'], locked_uids, unlocked_uids)
            return objects
