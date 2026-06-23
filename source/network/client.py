__author__ = 'yuanyu'

"""Client network layer — WebSocket in a background thread."""

import asyncio
import json
import threading
import time
import queue
import logging

from .protocol import (
    encode_message, decode_message,
    C2S_JOIN_ROOM, C2S_READY, C2S_PLACE_PLANT,
    C2S_SPAWN_ZOMBIE, C2S_COLLECT_SUN, C2S_PING,
    S2C_ROLE_ASSIGNED, S2C_GAME_START, S2C_STATE_SYNC,
    S2C_ACTION_RESULT, S2C_GAME_OVER, S2C_PONG,
    S2C_ERROR, S2C_OPPONENT_READY,
    S2C_OPPONENT_DISCONNECTED, S2C_ROOM_INFO,
)

logger = logging.getLogger('net-client')


class NetworkClient:
    def __init__(self, host='127.0.0.1', port=8765):
        self.host = host
        self.port = port
        self.uri = f'ws://{host}:{port}'
        self.incoming = queue.Queue()
        self.outgoing = queue.Queue()
        self.connected = False
        self.role = None
        self.room_id = None
        self.opponent_ready = False
        self.game_started = False
        self.game_over_data = None
        self.latest_state = None
        self.last_state_update = 0.0
        self._loop = None
        self._thread = None
        self._running = False

    # -- public API ---------------------------------------------------------

    def connect(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop,
                                        daemon=True)
        self._thread.start()

    def disconnect(self):
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2)
        self.connected = False

    def send(self, msg_type, data=None):
        self.outgoing.put(encode_message(msg_type, data or {}))

    def poll(self):
        msgs = []
        while True:
            try:
                msgs.append(self.incoming.get_nowait())
            except queue.Empty:
                break
        return msgs

    def join_room(self, room_id=''):
        self.send(C2S_JOIN_ROOM, {'room_id': room_id})

    def set_ready(self):
        self.send(C2S_READY, {})

    def place_plant(self, plant_type, grid_x, grid_y):
        self.send(C2S_PLACE_PLANT,
                  {'plant_type': plant_type, 'grid_x': grid_x, 'grid_y': grid_y})

    def spawn_zombie(self, zombie_type, lane):
        self.send(C2S_SPAWN_ZOMBIE, {'zombie_type': zombie_type, 'lane': lane})

    def collect_sun(self, sun_id):
        self.send(C2S_COLLECT_SUN, {'sun_id': sun_id})

    def send_ping(self):
        self.send(C2S_PING, {'client_time': time.time() * 1000})

    # -- internal -----------------------------------------------------------

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._client_loop())
        except Exception as e:
            logger.error("Network loop error: %s", e)
        finally:
            self._loop.close()

    async def _client_loop(self):
        try:
            import websockets
        except ImportError:
            logger.error("pip install websockets")
            self._running = False
            return
        try:
            async with websockets.connect(self.uri) as ws:
                self.connected = True
                self.incoming.put(('connected', {}))
                await asyncio.gather(self._recv_loop(ws),
                                     self._send_loop(ws))
        except Exception as e:
            logger.error("Connection error: %s", e)
            self.incoming.put(('error', {'message': str(e)}))
        finally:
            self.connected = False
            self.incoming.put(('disconnected', {}))

    async def _recv_loop(self, ws):
        while self._running:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                t, d = decode_message(raw)
                self.incoming.put((t, d))
                self._update_state(t, d)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self._running:
                    logger.error("recv error: %s", e)
                break

    async def _send_loop(self, ws):
        while self._running:
            try:
                try:
                    raw = self.outgoing.get_nowait()
                    await ws.send(raw)
                except queue.Empty:
                    await asyncio.sleep(0.01)
            except Exception as e:
                if self._running:
                    logger.error("send error: %s", e)
                break

    def _update_state(self, t, d):
        if t == S2C_ROLE_ASSIGNED:
            self.role = d.get('role')
            self.room_id = d.get('room_id')
        elif t == S2C_OPPONENT_READY:
            self.opponent_ready = True
        elif t == S2C_GAME_START:
            self.game_started = True
            self.game_over_data = None
            self.latest_state = d
        elif t == S2C_STATE_SYNC:
            self.latest_state = d
            self.last_state_update = time.time()
        elif t == S2C_GAME_OVER:
            self.game_over_data = d
            self.game_started = False
        elif t == S2C_ERROR:
            logger.warning("Server error: %s", d.get('message'))
