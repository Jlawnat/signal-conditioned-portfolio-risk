# Table sources

`python3 scripts/paper/generate.py` generates five Markdown tables from `audit/p3_abc_v5u_282d_comparison.json`, `audit/p3_abc_282d_comparison.json`, `audit/p3_abc_v5u_282_constraints.json`, and V5-U daily/trade files. Table 1 describes policies; Table 2 reports V5-U outcomes; Table 3 reports observational constraints; Table 4 keeps V4 and V5-U separate; Table 5 maps validation limitations. The script checks daily risk reconstruction against stored summary counts before writing tables. The PDF/SVG figures and table values use no cash-interest shadow outputs.
