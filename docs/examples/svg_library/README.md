# Structured SVG Library Example

This directory demonstrates how to structure layered SVG assets so they can be
referenced by the AI Context Framework during generation tasks. The examples
follow the conventions described in
[`docs/svg_layered_generation.md`](../../svg_layered_generation.md) and provide a
miniature library that pairs markup with machine-readable metadata.

## Directory Layout

```
svg_library/
  characters/
    hero.svg
    hero.meta.json
  backgrounds/
    cityscape.svg
    cityscape.meta.yaml
  effects/
    sun_glow.svg
    sun_glow.meta.json
```

Each SVG is organised into semantic `<g>` groups whose `id` attributes encode
their role. Palette tokens are expressed as CSS variables or named gradients, so
prompts can reference reusable colour schemes without editing raw hex values.

The metadata sidecars summarise the visual intent of each group, record bounding
box hints, and list any palettes or blend modes that downstream tools should
apply. These files can be ingested into a context map under a `visual_assets`
channel so the language model can plan compositions.

## Sample Context Packet Entry

```jsonc
{
  "channel": "visual_assets",
  "asset": "characters/hero.svg",
  "summary": "Hero character with cape and emblem for foreground placement.",
  "groups": [
    { "id": "hero_character/body", "role": "primary figure" },
    { "id": "hero_character/cape", "role": "dynamic cape" },
    { "id": "hero_character/emblem", "role": "accent" }
  ],
  "palette_tokens": ["--skin", "--cape", "--suit", "--accent"],
  "bounding_boxes": {
    "hero_character/body": { "x": 70, "y": 60, "width": 60, "height": 100 }
  }
}
```

## Example Layer Plan Output

```jsonc
{
  "canvas": { "width": 1920, "height": 1080 },
  "layers": [
    {
      "source": "backgrounds/cityscape.svg#cityscape/background",
      "zIndex": 0
    },
    {
      "source": "backgrounds/cityscape.svg#cityscape/buildings-back",
      "transform": "translate(0, 20)",
      "opacity": 0.85
    },
    {
      "source": "characters/hero.svg#hero_character/body",
      "transform": "translate(860, 420) scale(2.2)"
    },
    {
      "source": "characters/hero.svg#hero_character/cape",
      "transform": "translate(840, 400) scale(2.2)",
      "blend": "normal"
    },
    {
      "source": "effects/sun_glow.svg",
      "transform": "translate(760, 260) scale(3.2)",
      "blend": "screen",
      "opacity": 0.9
    }
  ]
}
```

This plan demonstrates how the metadata can guide the model to compose existing
layers without rasterising new artwork.
