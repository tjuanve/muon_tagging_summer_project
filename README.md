# muon_tagging

## Background

The High-Energy Starting Event (HESE) selection identifies neutrino interactions whose vertex is fully contained within the IceCube detector, using the outer layer of DOMs as an active veto against incoming atmospheric muons. Despite this veto, a residual muon background survives: dim muons that enter the detector without triggering enough veto DOMs can mimic a starting event, particularly at lower deposited energies.

The standard approach to estimating this background is a data-driven veto method. Rather than relying on muon simulation, which is both computationally expensive and statistically limited, the background rate is estimated directly from the data by applying a second veto on a shrunk version of the detector (DetectorShrinker). Events passing the outer veto but failing the inner one provide a control sample from which the leakage into the signal region can be determined. This method was developed for the original HESE analyses and is described in detail in the references below.

The existing background estimate is now outdated. The goal of this project is to rerun the veto method on the full dataset available today, and to study whether the muon background rate shows any variation across years, seasons, or detector conditions that could bias the analysis.

## References

- [HESE analysis — PhysRevD.104.022002](https://link.aps.org/pdf/10.1103/PhysRevD.104.022002?casa_token=H7y0jrC3v_QAAAAA:FMkD55CWGfLdNWsJTmCA-OGBTCF2v6WKMW3x7hTK0oHl6zk9_0IIYfJWm_oafFLOecd9jhRsyyMLK77K)
- [HESE flavor composition measurement — PhD thesis (HU Berlin)](https://edoc.hu-berlin.de/items/b762d844-4705-4710-8746-9a587e33becc)
- [High-Energy Starting Track Event Search — IceCube Wiki](https://wiki.icecube.wisc.edu/index.php/High-Energy_Starting_Track_Event_Search#Atmospheric_Muon_Background)
- [VHESelfVeto — icetray documentation](https://docs.icecube.aq/icetray/main/projects/VHESelfVeto/index.html)

## Pipeline

`run_vheselfveto.py` runs the following chain on IceCube level2 data:

1. **VHESelfVeto** (full geometry) — slides a time window through HLC pulses to find a vertex candidate and checks whether any charge arrived in the veto region before that vertex time.
2. **DetectorShrinker** — produces a trimmed geometry and pulse series by removing the outermost layer of the detector, used to estimate the nested-veto passing rate.
3. **VHESelfVeto** (shrunk geometry) — repeats the veto on the trimmed detector.

At the end of each run the script prints per-veto statistics and a cross-comparison table showing, for each outcome of the full-geometry veto, how the same events were classified by the shrunk-geometry veto.

Output frame keys written per event (defaults):

| Key | Content |
|-----|---------|
| `HomogenizedQTot` | `I3Double` — total charge excluding DeepCore (homogenized), full geometry |
| `CausalQTot` | `I3Double` — charge from pulses causally connected to the vertex, full geometry |
| `VHESelfVeto` | `I3Bool` — `True` if vetoed, full geometry |
| `VHESelfVetoVertexTime` | `I3Double` — vertex time estimate, full geometry |
| `VHESelfVetoVertexPos` | `I3Position` — vertex position estimate, full geometry |
| `HomogenizedQTotShrunk` | `I3Double` — total charge excluding DeepCore (homogenized), shrunk geometry |
| `CausalQTotShrunk` | `I3Double` — charge from pulses causally connected to the vertex, shrunk geometry |
| `VHESelfVetoShrunk` | `I3Bool` — `True` if vetoed, shrunk geometry |
| `VHESelfVetoShrunkVertexTime` | `I3Double` — vertex time estimate, shrunk geometry |
| `VHESelfVetoShrunkVertexPos` | `I3Position` — vertex position estimate, shrunk geometry |

## Usage

```bash
./test_run.sh
```

or directly:

```bash
/cvmfs/icecube.opensciencegrid.org/py3-v4.4.1/RHEL_7_x86_64_v2/metaprojects/icetray/v1.14.0/bin/icetray-shell \
    /cvmfs/icecube.opensciencegrid.org/users/tvaneede/venv/py3-v4.4.1_reco-v1.1.0/bin/python \
    run_vheselfveto.py \
    -g <GCD.i3.zst> \
    -o <output.i3.zst> \
    <datafile.i3.zst> [...]
```

## Arguments

### Required

| Argument | Description |
|----------|-------------|
| `-g`, `--gcd` | GCD file |
| `-o`, `--output` | Output `.i3` file |
| `inputfiles` | One or more input `.i3` data files |

### VHESelfVeto (full geometry)

| Argument | Default | Description |
|----------|---------|-------------|
| `--pulses` | `SplitInIcePulses` | Input pulse series |
| `--geometry` | `I3Geometry` | Geometry object |
| `--top-boundary-width` | `90` m | Veto thickness at top and sides |
| `--bottom-boundary-width` | `10` m | Veto thickness at the bottom |
| `--dust-layer` | `-135` m | Z coordinate of the dust layer |
| `--dust-layer-width` | `80` m | Boundary width below the dust layer |
| `--time-window` | `3000` ns | Sliding time window size |
| `--vertex-threshold` | `250` PE | Charge in window to declare a vertex |
| `--veto-threshold` | `3` PE | Max charge in veto region before vertex |
| `--output-bool` | `VHESelfVeto` | Base name for output frame keys; `VertexTime` and `VertexPos` are appended for the other two keys |
| `--select-passing-inner` | off | Only write events that pass the outer veto but are vetoed by the shrunk-geometry veto |

### DetectorShrinker

| Argument | Default | Description |
|----------|---------|-------------|
| `--ds-top-boundary-width` | `90` m | Top/side boundary width for shrinking |
| `--ds-bottom-boundary-width` | `10` m | Bottom boundary width for shrinking |

The shrinker derives its input pulse series and geometry from `--pulses` and `--geometry`, and writes the trimmed versions under `<pulses>Trimmed` and `<geometry>Trimmed`.

## Output

### Per-veto summary

Printed for both the full and shrunk geometry:

```
=== VHESelfVeto (full geometry) ===
  Total physics frames :  1000
  Passed veto          :   420
  Vetoed               :   570
  No vertex found      :    10
```

### Event selection (`--select-passing-inner`)

When enabled, only events that **pass the outer (full-geometry) veto** and are **vetoed by the inner (shrunk-geometry) veto** are written to the output file. These are muons that slipped through the outer veto undetected but were caught by the inner veto. They form the control sample used to extrapolate the muon leakage rate into the signal region.

Counting and the cross-comparison are always run over all events regardless of this flag.

### Cross-comparison

Breaks down each full-geometry outcome by the shrunk-geometry result, with percentages within each row:

```
=== Cross-comparison: full vs shrunk geometry ===

  Full geometry: passed (420 events)
    Shrunk passed      :    390  ( 92.9%)
    Shrunk vetoed      :     28  (  6.7%)
    Shrunk no_vertex   :      2  (  0.5%)

  Full geometry: vetoed (570 events)
    Shrunk passed      :     15  (  2.6%)
    Shrunk vetoed      :    553  ( 97.0%)
    Shrunk no_vertex   :      2  (  0.4%)
```

## Batch processing (HTCondor DAG)

`create_dag.py` creates an HTCondor DAG that submits one job per subrun across any number of years, reading the good-run lists from the standard `IC86_{year}_GoodRunInfo.txt` files. Must be run inside `icetray-shell` since it reads GCD files to apply the active string check.

**Burn sample (default):** by default only runs whose run number ends in 0 are processed. This is the standard IceCube burn sample (~10% of the data), used for initial validation before committing to the full dataset. Pass `--no-burn-sample` to process all good runs.

**Active string requirement (default on):** each run's GCD file is read to verify that the detector meets the quality requirements used in the HESE analysis: at least 83 active in-ice strings and no inactive strings in the outer detector layer. Runs that fail are skipped. Pass `--no-active-string-check` to disable.

```bash
# Burn sample only (default), with active string check
icetray-shell python create_dag.py --years 2014 2015

# Full dataset
icetray-shell python create_dag.py --years 2014 2015 --no-burn-sample

# Create and submit immediately
icetray-shell python create_dag.py --years 2014 2015 --submit
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--years` | *(required)* | One or more years to process |
| `--output-dir` | `muon_tagging/output` | Root directory for output `.i3` files |
| `--dag-dir` | `/scratch/tvaneede/muon_tagging` | Directory for DAG files and logs |
| `--dag-name` | `vheselfveto` | Prefix for the DAG directory name |
| `--no-burn-sample` | off | Process all good runs instead of burn sample only |
| `--no-active-string-check` | off | Skip the active string requirement check |
| `--max-runs` | *(all)* | Process only the first N runs per year |
| `--submit` | off | Submit the DAG with `condor_submit_dag` after writing it |

Output files are written to `<output-dir>/IC86_{year}/{RunNNNNNN}/<stem>_VHESelfVeto.i3.zst`. Logs go to `<dag-dir>/logs/`.

## Test run

`test_run.sh` runs on a single subrun from IC86 2014 data:

- **Run:** `Run00124550` (first good run in `IC86_2014_GoodRunInfo.txt`)
- **GCD:** co-located in the run directory
- **Data:** subrun `00000000`
- **Output:** `output_Run00124550_sub00.i3.zst`
- **Log:** `test_run.log`
