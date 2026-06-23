# Dev Log (multiplayer branch)

## 2026-06-18
### Fixed
- **Zombie card crash**: `tool.GFX.get(gfx_key)` was silently returning `None`
  and the fallback code was wrong.  Now uses `tool.GFX[gfx_key]` and if the
  value is a list takes `frame[0]`, then passes the single Surface to
  `tool.get_image()`.  All five zombie types load correctly.
- **All previous fixes**: lobby text input, scene transitions, zombie images,
  card cooldowns, car animation, bullet alignment, melee-plant attacks,
  cherry-bomb ash, engine dedup.
