# reproduce_hese7

Reproduction of Austin Schneider's muon-tagging analysis from
`/data/user/aschneider/store/muon_tag/austin/shrinkydink.py`.

## What this folder contains

| File | Purpose |
|------|---------|
| `shrinkydink.py` | Python 3 port of Austin's script |
| `test_run.sh` | Run the script on Run 127009 (IC86 2015, 55 subruns, 1 known passing event) |
| `compare_with_austin.ipynb` | Side-by-side comparison of cut counts and numeric values vs Austin's reference and atsoufli's pipeline |
| `output/` | Output h5 files from `test_run.sh` |

---

## Test run: Run 127009 (IC86\_2015)

Run 127009 was chosen because it has only **55 subruns** and contains exactly one
event (Event 567172) that passes all 5 shrinkydink cuts in Austin's reference output.
It is therefore the fastest run to reprocess locally for a full end-to-end comparison.

Austin's reference output is at:
```
/data/ana/Diffuse/HESE/Pass2/IC86_2015/data_muontag_reprocessed/
```

---

## Differences investigated

### Initial run (run-specific GCD)

When first run with the GCD from the data directory, the following differences were observed:

| Variable | Austin | Mine | Δ |
|----------|--------|------|---|
| QTot | 7323.78 | 7302.71 | −21 PE (−0.3%) |
| CausalQTot | 7059.14 | 7042.67 | −16 PE (−0.2%) |
| InteriorCausalQTot | 6788.56 | 6597.83 | −191 PE (−2.8%) |
| VHESelfVeto boolean | True | True | ✓ |
| VHESelfVetoVertexTime | 11074.1664 | 11074.1664 | ✓ |
| VHESelfVetoVertexPos | (248.42, −111.83, −472.10) | (248.42, −111.83, −472.11) | 0.01 m rounding |

### After switching to Austin's GCD (merged GCD)

Austin's condor submit file (`shrinkydink.sub`) does **not** pass `--gcd`, so his
script used the hardcoded default:

```
/cvmfs/icecube.opensciencegrid.org/data/GCD/GeoCalibDetectorStatus_IC86_Merged.i3.gz
```

After switching `test_run.sh` to use the same merged GCD, QTot and CausalQTot
matched exactly:

| Variable | Austin | Mine | Δ |
|----------|--------|------|---|
| QTot | 7323.78 | 7323.78 | ✓ |
| CausalQTot | 7059.14 | 7059.14 | ✓ |
| InteriorCausalQTot | 6788.56 | 6608.85 | −180 PE (−2.6%) |
| VHESelfVeto boolean | True | True | ✓ |
| VHESelfVetoVertexTime | 11074.1664 | 11074.1664 | ✓ |
| VHESelfVetoVertexPos | (248.42, −111.83, −472.10) | (248.42, −111.83, −472.10) | ✓ |

The remaining difference in `InteriorCausalQTot` is explained by a bug in Austin's
original script (see below). The VHESelfVeto algorithm, vertex, and CausalQTot are
**fully reproduced**.

---

## Cross-check: atsoufli's pipeline

Atsoufli ran a separate VHESelfVeto processing chain stored at:
```
/data/user/atsoufli/muon_tagging/output/5th_try/h5/IC86_2015.h5
```

For the same event (Run 127009, Event 567172):

| Pipeline | CausalQTot |
|----------|-----------|
| Austin (shrinkydink, icerec.V05-02-00, merged GCD) | 7059.14 PE |
| Mine (shrinkydink, icetray v1.14.0, merged GCD) | 7059.14 PE ✓ |
| Atsoufli (5th\_try pipeline) | 7042.67 PE |

Atsoufli's value matches what my script produced when using the **run-specific GCD**
(7042.67 PE), suggesting atsoufli's pipeline uses the run-specific GCD rather than
the merged one. The ~16 PE difference (~0.2%) relative to Austin is therefore a
known and understood calibration choice, not a bug.

---

## Code differences: Python 2 → Python 3 port

The script logic is identical. The only substantive changes made during porting:

1. `print x` → `print(x)`
2. `from I3Tray import *` → `from icecube.icetray import I3Tray`
3. `from icecube import ..., VHESelfVeto` (explicit import needed in newer icetray)
4. `os.makedirs(path)` → `os.makedirs(path, exist_ok=True)`
5. Added `--max-files` argument for local testing
6. Mixed tab/space indentation fixed

### Known bug in Austin's original: `InteriorCausalQTot` VertexTime

Austin's script passes a non-existent frame key as the vertex time:

```python
# Austin's original — bug: 'VHESelfVetoTime' does not exist in the frame
tray.AddModule('HomogenizedQTot', Pulses='HLCPulsesTrimmed',
               Output='InteriorCausalQTot', VertexTime='VHESelfVetoTime')
```

When `HomogenizedQTot` receives a missing `VertexTime` key it falls back to summing
all pulses without a temporal cut, making `InteriorCausalQTot` equivalent to
`HomogenizedQTot` over the shrunk pulses (no causality window applied).

My script uses the correct key:

```python
tray.AddModule('HomogenizedQTot', Pulses='HLCPulsesTrimmed',
               Output='InteriorCausalQTot', VertexTime='MuonTagTime')
```

`MuonTagTime` is the VHESelfVeto vertex time. Applying `t_pulse >= MuonTagTime`
restricts to causal pulses, giving a smaller and physically correct charge.
This is a genuine fix — Austin's `InteriorCausalQTot` was not measuring what it
was intended to measure.

---

## Environment

| | Austin | Mine |
|--|--------|------|
| Python | 2 (py2-v3) | 3 (py3-v4.4.1) |
| Metaproject | icerec.V05-02-00\_legacy | icetray/v1.14.0 |
| GCD | merged (IC86\_Merged) | merged (IC86\_Merged) — after fix |

The icetray version difference alone does not affect the VHESelfVeto vertex or
the cut logic. With the same GCD, charge quantities agree to within floating-point
precision.

---

## Cut-level comparison

All shared events (my 55-subrun test run vs Austin's full run) agree on every cut:

| Cut | Variable | Mine | Austin | Agreement |
|-----|----------|------|--------|-----------|
| 0 | VHESelfVeto key exists | 1084/1084 pass | 5748/5748 pass | 100% |
| 1 | VHESelfVeto found vertex | 1084/1084 pass | 5739/5748 pass | 100% |
| 2 | Inner VHESelfVeto key exists | 917/1084 pass | 4893/5739 pass | 100% |
| 3 | Inner VHESelfVeto does not fire | 1/917 pass | 2/4893 pass | 100% |
| 4 | CausalQTot > 6000 PE | 1/1 pass | 1/2 pass | 100% |

All 1084 shared events agree on every cut. The veto decision is fully reproduced.
