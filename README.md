# AI.KML

Lightweight automated KML toolkit for:

1. Learning and developing with expert KML resources  
2. Atomically creating and cleaning `.kml` outputs  
3. Applying creative daily overlays that evolve with feedback

## Quick start

Run from the repository root:

```bash
python /home/runner/work/AI.KML/AI.KML/kml_automation.py resources
```

Build a complete KML file atomically (create → clean → overlay):

```bash
python /home/runner/work/AI.KML/AI.KML/kml_automation.py build \
  --output /home/runner/work/AI.KML/AI.KML/output/demo.kml \
  --name "Demo Point" \
  --latitude 13.47 \
  --longitude 144.69 \
  --description "Daily generated KML"
```

## Commands

- `resources` – KML standards, docs, and practical guidance
- `create` – create a base KML placemark
- `clean` – normalize whitespace, coordinate formatting, and placemark ordering
- `overlay` – apply a daily style overlay to existing KML
- `build` – atomic one-command pipeline: create + clean + overlay
- `suggest-overlay` – preview the style chosen for a date
- `record-feedback` – save votes/notes to influence future daily styles

## Daily feedback loop

Create/update feedback:

```bash
python /home/runner/work/AI.KML/AI.KML/kml_automation.py record-feedback \
  --feedback-file /home/runner/work/AI.KML/AI.KML/output/overlay_feedback.json \
  --overlay-id sunrise \
  --vote 1 \
  --note "Use this more often for storytelling maps."
```

Use the same feedback file in `build`, `overlay`, or `suggest-overlay` commands to steer future daily overlay selection.
