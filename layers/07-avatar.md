# Layer 7: Avatar

**Gives the agent:** a profile picture for every account.
**Human needed:** none. **Cost:** free.
**Identity keys:** `face.photo`, `face.seed`

It is not a human face and not a glass ball. It is a mark of flowing luminous ribbons on a dark disc, with colours and curves that belong to this agent alone. The dashboard animates the same mark live.

`python3 humanize.py init` already draws it. To redraw or repair it:

```bash
python3 humanize.py avatar            # installs Pillow into ~/.humanize/pydeps if needed, writes ~/.humanize/face.png
```

The palette and ribbon shapes are derived from a hash of `face.seed`, so the same seed always gives the same mark. Upload `~/.humanize/face.png` as the avatar on every account in Layers 6 and 14.

Never regenerate it once accounts carry it. If the human renames the agent, the mark stays, because `face.seed` does not change. Without Pillow the dashboard still draws the avatar live; only the PNG file is skipped.
