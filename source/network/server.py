import asyncio
import json
import logging
import time

from .protocol import (
    encode_message, decode_message,
    C2S_JOIN_ROOM, C2S_READY, C2S_PLACE_PLANT,
    C2S_SPAWN_ZOMBIE, C2S_COLLECT_SUN, C2S_PING,
    S2C_ROLE_ASSIGNED, S2C_GAME_START, S2C_STATE_SYNC,
    S2C_ACTION_RESULT, S2C_GAME_OVER, S2C_PONG,
    S2C_ERROR, S2C_OPPONENT_READY, S2C_OPPONENT_DISCONNECTED,
    S2C_ROOM_INFO,
    ROLE_PLANTS, ROLE_ZOMBIES,
)
from .. import constants as c
from .engine import Simulator

# plant cost / cooldown maps (extracted, no pygame dep)
PLANT_COST_MAP = {
    c.SUNFLOWER: 50, c.PEASHOOTER: 100, c.SNOWPEASHOOTER: 175, c.WALLNUT: 50,
    c.CHERRYBOMB: 150, c.THREEPEASHOOTER: 325, c.REPEATERPEA: 200, c.CHOMPER: 150,
    c.PUFFSHROOM: 0, c.POTATOMINE: 25, c.SQUASH: 50, c.SPIKEWEED: 100,
    c.JALAPENO: 125, c.SCAREDYSHROOM: 25, c.SUNSHROOM: 25, c.ICESHROOM: 75,
    c.HYPNOSHROOM: 75, c.WALLNUTBOWLING: 0, c.REDWALLNUTBOWLING: 0,
}
PLANT_COOLDOWN_MAP = {
    c.SUNFLOWER: 7500, c.PEASHOOTER: 7500, c.SNOWPEASHOOTER: 7500, c.WALLNUT: 30000,
    c.CHERRYBOMB: 50000, c.THREEPEASHOOTER: 7500, c.REPEATERPEA: 7500, c.CHOMPER: 7500,
    c.PUFFSHROOM: 7500, c.POTATOMINE: 30000, c.SQUASH: 30000, c.SPIKEWEED: 7500,
    c.JALAPENO: 50000, c.SCAREDYSHROOM: 7500, c.SUNSHROOM: 7500, c.ICESHROOM: 50000,
    c.HYPNOSHROOM: 30000, c.WALLNUTBOWLING: 0, c.REDWALLNUTBOWLING: 0,
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('pvz-server')


# ---------------------------------------------------------------------------
#  Room
# ---------------------------------------------------------------------------

class Room:
    def __init__(self, room_id, manager):
        self.id = room_id
        self.manager = manager
        self.players = {}          # role -> websocket
        self.player_addrs = {}
        self.ready = set()
        self.state = 'waiting'
        self.sim = Simulator(is_day=True)
        self.game_task = None

    # -- player management --------------------------------------------------

    def add_player(self, ws, addr=None):
        role = None
        # 总是先尝试 plants，再尝试 zombies
        for r in (ROLE_PLANTS, ROLE_ZOMBIES):
            if r not in self.players:
                self.players[r] = ws
                self.player_addrs[r] = addr
                role = r
                break

        if role is not None:
            logger.info("[%s] %s joined (addr=%s)", self.id, role, addr)
            # 先给当前玩家分配角色
            asyncio.create_task(self._send(role, S2C_ROLE_ASSIGNED,
                                           {'role': role, 'room_id': self.id}))
            # 如果现在满 2 人，通知双方房间信息
            if len(self.players) == 2:
                other = ROLE_ZOMBIES if role == ROLE_PLANTS else ROLE_PLANTS
                asyncio.create_task(self._send(other, S2C_ROOM_INFO,
                                               {'room_id': self.id,
                                                'players': 2,
                                                'state': 'waiting'}))
                # 再给当前玩家也发一份 room_info
                asyncio.create_task(self._send(role, S2C_ROOM_INFO,
                                               {'room_id': self.id,
                                                'players': 2,
                                                'state': 'waiting'}))

        return role

    def remove_player(self, ws):
        role = self._find_role(ws)
        if not role:
            return
        logger.info("[%s] %s disconnected", self.id, role)
        del self.players[role]
        self.player_addrs.pop(role, None)
        self.ready.discard(role)
        if self.state == 'playing':
            other = self._other(role)
            if other in self.players:
                # 先发 game_over → 对手客户端弹出 "You Win!" 并自动回主菜单
                asyncio.create_task(self._send(other, S2C_GAME_OVER,
                                               {'winner': other,
                                                'reason': 'opponent_disconnected'}))
            self.manager.close_room(self.id, 'player_disconnected')
        else:
            # 等待中的房间，通知对手断开
            other = self._other(role)
            if other in self.players:
                asyncio.create_task(self._send(other, S2C_OPPONENT_DISCONNECTED,
                                               {'message': 'Opponent disconnected'}))
            # 如果房间被清空则立即关闭
            if not any(r in self.players for r in (ROLE_PLANTS, ROLE_ZOMBIES)):
                self.manager.close_room(self.id, 'player_disconnected')

    # -- ready / start ------------------------------------------------------

    def set_ready(self, ws):
        role = self._find_role(ws)
        if not role:
            return
        self.ready.add(role)
        logger.info("[%s] %s ready (ready=%s players=%d)",
                    self.id, role, self.ready, len(self.players))
        other = self._other(role)
        if other in self.players:
            asyncio.create_task(self._send(other, S2C_OPPONENT_READY,
                                           {'ready': True}))
        if len(self.ready) == 2 and len(self.players) == 2:
            logger.info("[%s] Both ready – starting game", self.id)
            asyncio.create_task(self._start_game())

    async def _start_game(self):
        self.state = 'playing'
        self.sim.start_game()
        logger.info("[%s] Game started", self.id)
        await self._broadcast(S2C_GAME_START, {
            'message': 'Game started!',
            'sun_value': self.sim.state.sun_value,
            'brain_points': self.sim.state.brain_points,
            'grid_width': c.GRID_X_LEN,
            'grid_height': c.GRID_Y_LEN,
        })
        self.game_task = asyncio.create_task(self._game_loop())

    async def _game_loop(self):
        TICK = 0.05
        try:
            while self.state == 'playing':
                t0 = time.time()
                self.sim.tick(50)
                if self.sim.state.state == 'finished':
                    await self._game_over()
                    break
                await self._broadcast(S2C_STATE_SYNC,
                                      self.sim.state.get_snapshot())
                elapsed = time.time() - t0
                if elapsed < TICK:
                    await asyncio.sleep(TICK - elapsed)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("[%s] loop error: %s", self.id, e)

    async def _game_over(self):
        w = self.sim.state.winner
        logger.info("[%s] Game over – winner=%s", self.id, w)
        await self._broadcast(S2C_GAME_OVER, {
            'winner': w,
            'stats': {'plants_placed': len(self.sim.state.plants),
                      'zombies_spawned': len([z for z in self.sim.state.zombies
                                              if not z.is_hypno]),
                      'game_time': self.sim.state.game_time},
        })
        self.state = 'finished'
        # 一局结束后立即关闭房间，释放所有连接
        asyncio.create_task(self._delayed_cleanup(delay=1))

    async def _delayed_cleanup(self, delay=10):
        await asyncio.sleep(delay)
        self.manager.close_room(self.id, 'game_finished')

    # -- actions ------------------------------------------------------------

    async def handle_action(self, ws, msg_type, data):
        role = self._find_role(ws)
        if not role:
            return

        if msg_type == C2S_READY:
            self.set_ready(ws)

        elif msg_type == C2S_PLACE_PLANT:
            if role != ROLE_PLANTS:
                return await self._err(ws, "You are not the plant player")
            if self.state != 'playing':
                return await self._err(ws, "Game not started")
            ok, err = self.sim.place_plant(
                data['plant_type'], data['grid_x'], data['grid_y'],
                PLANT_COST_MAP.get(data['plant_type'], 0),
                PLANT_COOLDOWN_MAP.get(data['plant_type'], 7500))
            await self._send(role, S2C_ACTION_RESULT,
                             {'action': 'place_plant', 'success': ok,
                              'error': err,
                              'sun_value': self.sim.state.sun_value})

        elif msg_type == C2S_SPAWN_ZOMBIE:
            if role != ROLE_ZOMBIES:
                return await self._err(ws, "You are not the zombie player")
            if self.state != 'playing':
                return await self._err(ws, "Game not started")
            ok, err = self.sim.spawn_zombie(data['zombie_type'], data['lane'])
            await self._send(role, S2C_ACTION_RESULT,
                             {'action': 'spawn_zombie', 'success': ok,
                              'error': err,
                              'brain_points': self.sim.state.brain_points})

        elif msg_type == C2S_COLLECT_SUN:
            if role != ROLE_PLANTS:
                return
            ok, val = self.sim.collect_sun(data['sun_id'])
            if ok:
                await self._send(role, S2C_ACTION_RESULT,
                                 {'action': 'collect_sun', 'success': True,
                                  'sun_value': self.sim.state.sun_value})

        elif msg_type == C2S_PING:
            await self._send(role, S2C_PONG,
                             {'server_time': time.time() * 1000,
                              'client_time': data.get('client_time', 0)})

    # -- helpers ------------------------------------------------------------

    async def _err(self, ws, msg):
        try:
            await ws.send(encode_message(S2C_ERROR, {'message': msg}))
        except Exception:
            pass

    async def _send(self, role, t, d):
        ws = self.players.get(role)
        if ws:
            try:
                await ws.send(encode_message(t, d))
            except Exception:
                pass

    async def _broadcast(self, t, d):
        for ws in list(self.players.values()):
            try:
                await ws.send(encode_message(t, d))
            except Exception:
                pass

    async def kick_all(self, reason='room_closed'):
        await self._broadcast(S2C_GAME_OVER, {'winner': None, 'reason': reason})
        for ws in list(self.players.values()):
            try:
                await ws.close()
            except Exception:
                pass
        self.players.clear()
        self.player_addrs.clear()
        self.ready.clear()

    def _find_role(self, ws):
        for r, w in self.players.items():
            if w is ws:
                return r
        return None

    def _other(self, role):
        return ROLE_ZOMBIES if role == ROLE_PLANTS else ROLE_PLANTS

    def is_empty(self):
        return len(self.players) == 0

    def is_expired(self):
        return self.is_empty() and self.state in ('waiting', 'finished')


# ---------------------------------------------------------------------------
#  RoomManager
# ---------------------------------------------------------------------------

class RoomManager:
    def __init__(self):
        self.rooms = {}
        self._ws_to_room = {}
        self._next = 1000

    def create_room(self):
        rid = f"{self._next:06d}"
        self._next += 1
        r = Room(rid, self)
        self.rooms[rid] = r
        logger.info("Room %s created", rid)
        return r

    def find_or_create_room(self):
        for r in self.rooms.values():
            if r.state == 'waiting' and len(r.players) < 2:
                return r
        return self.create_room()

    def close_room(self, rid, reason=''):
        r = self.rooms.pop(rid, None)
        if r is None:
            return
        logger.info("Room %s closed (%s)", rid, reason)
        if r.game_task:
            r.game_task.cancel()
        for ws in list(r.players.values()):
            self._ws_to_room.pop(ws, None)
        r.players.clear()

    def cleanup_expired(self):
        for rid in list(self.rooms):
            if self.rooms[rid].is_expired():
                logger.info("Cleaning expired room %s", rid)
                del self.rooms[rid]


# ---------------------------------------------------------------------------
#  WebSocket handler
# ---------------------------------------------------------------------------

async def handle_connection(websocket, path, mgr):
    addr = websocket.remote_address
    logger.info("New connection: %s", addr)
    room = None
    try:
        async for raw in websocket:
            try:
                t, d = decode_message(raw)
            except json.JSONDecodeError:
                await websocket.send(encode_message(S2C_ERROR,
                                     {'message': 'Invalid JSON'}))
                continue
            logger.debug("[%s] recv: %s", addr, t)

            if t == C2S_JOIN_ROOM:
                req = d.get('room_id', '')
                if req:
                    # 玩家指定了房间号 → 使用该房间或按需创建
                    target = mgr.rooms.get(req)
                    if target is None:
                        # 房间不存在 → 以用户指定的 ID 创建
                        target = Room(req, mgr)
                        mgr.rooms[req] = target
                        logger.info("Room %s created (by player request)", req)
                    elif target.state != 'waiting':
                        await websocket.send(encode_message(S2C_ERROR,
                                             {'message': f'Room {req} is already in game'}))
                        continue
                    elif len(target.players) >= 2:
                        await websocket.send(encode_message(S2C_ERROR,
                                             {'message': 'Room full'}))
                        continue
                else:
                    # Quick Match：自动匹配
                    target = mgr.find_or_create_room()
                role = target.add_player(websocket, addr)
                if role is None:
                    await websocket.send(encode_message(S2C_ERROR,
                                         {'message': 'Cannot join room'}))
                    continue
                room = target
                mgr._ws_to_room[websocket] = room.id
                continue

            if room is None:
                await websocket.send(encode_message(S2C_ERROR,
                                     {'message': 'Join a room first'}))
                continue
            await room.handle_action(websocket, t, d)
    except Exception as e:
        logger.error("Error %s: %s", addr, e)
    finally:
        logger.info("Disconnected: %s", addr)
        if room:
            room.remove_player(websocket)
            mgr._ws_to_room.pop(websocket, None)
            if room.is_empty():
                mgr.close_room(room.id, 'all_disconnected')


async def periodic_cleanup(mgr, interval=30):
    while True:
        await asyncio.sleep(interval)
        mgr.cleanup_expired()


async def main_server(host='0.0.0.0', port=8765):
    try:
        import websockets
    except ImportError:
        logger.error("pip install websockets")
        return
    mgr = RoomManager()
    logger.info("PvP server ws://%s:%s", host, port)
    asyncio.create_task(periodic_cleanup(mgr))

    async def handler(ws):
        await handle_connection(ws, None, mgr)

    try:
        async with websockets.serve(handler, host, port):
            logger.info("Running... Ctrl+C to stop")
            await asyncio.Future()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        for rid in list(mgr.rooms):
            await mgr.rooms[rid].kick_all('server_shutdown')
        logger.info("Stopped")

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='PvZ PvP Server')
    p.add_argument('--host', default='0.0.0.0')
    p.add_argument('--port', type=int, default=8765)
    args = p.parse_args()
    asyncio.run(main_server(args.host, args.port))
