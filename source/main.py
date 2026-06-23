__author__ = 'yuanyu'

from . import tool
from . import constants as c
from .state import mainmenu, screen, level, lobby, multiplayer

def main():
    game = tool.Control()
    state_dict = {c.MAIN_MENU: mainmenu.Menu(),
                  c.GAME_VICTORY: screen.GameVictoryScreen(),
                  c.GAME_LOSE: screen.GameLoseScreen(),
                  c.LEVEL: level.Level(),
                  c.LOBBY: lobby.Lobby(),
                  c.MULTIPLAYER_LEVEL: multiplayer.MultiplayerLevel()}
    game.setup_states(state_dict, c.MAIN_MENU)
    game.main()