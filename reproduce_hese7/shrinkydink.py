#!/usr/bin/env python3
"""
Adapted from /data/user/aschneider/store/muon_tag/austin/shrinkydink.py
Ported to Python 3 / icetray v1.14.0.
"""

import argparse
import glob
import re
import sys

parser = argparse.ArgumentParser(description='Tag muons with shrunken detector')

parser.add_argument('--input', default=None, type=str, dest='input')
parser.add_argument('--year', default=None, type=str, dest='year')
parser.add_argument('--run', default=None, type=int, dest='run')
parser.add_argument('--output-prefix', default=None, type=str, dest='output_prefix')
parser.add_argument('--output-dir', default='.', type=str, dest='outdir')
parser.add_argument('--gcd',
    default='/cvmfs/icecube.opensciencegrid.org/data/GCD/GeoCalibDetectorStatus_IC86_Merged.i3.gz',
    type=str, dest='gcd')
parser.add_argument('--max-files', default=None, type=int, dest='max_files',
    help='Limit number of data files to process (for testing)')

args = parser.parse_args()

import os
os.makedirs(args.outdir, exist_ok=True)

from icecube.icetray import I3Tray
from icecube import icetray, dataio, dataclasses, DomTools, hdfwriter, VHESelfVeto

print(args.input)
if args.input is not None:
    args.input = args.input.strip("'").strip('"').strip("'")

run_max = 130475

seasons    = ['IC79_2010', 'IC86_2011', 'IC86_2012', 'IC86_2013', 'IC86_2014', 'IC86_2015', 'IC86_2016', 'IC86_2017']
years      = ['2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017']
active_strings = [79, 86, 86, 86, 86, 86, 86, 86]
subfolders = ['level2pass2', 'level2pass2', 'level2pass2', 'level2pass2', 'level2pass2', 'level2pass2', 'level2pass2', 'level2']

runinfo_fname_postfix = 'GoodRunInfo.txt'
base_path = '/data/exp/IceCube/'


def parse_runinfo_line(line, line_number, header=1):
    split_line = line.split()
    if len(split_line) < 8:
        if line_number > header:
            print(f'Line {line_number} does not have enough columns!')
        return None
    try:
        runNumber = int(split_line[0])
    except ValueError:
        if line_number > header:
            print(f'bad run number field: {split_line[0]}')
        return None
    if runNumber > run_max:
        return None
    try:
        good_i3 = int(split_line[1])
    except ValueError:
        if line_number > header:
            print(f'bad good_i3 field: {split_line[1]}')
        return None
    if good_i3 != 1:
        print('Bad i3!')
        return None
    try:
        duration = float(split_line[3])
    except ValueError:
        if line_number > header:
            print(f'bad duration field: {split_line[3]}')
        return None
    path = split_line[7]
    m = re.search('level2/(.+?)/', path) or re.search('level2pass2/(.+?)/', path)
    if not m:
        return None
    date = int(m.group(1))
    try:
        n_active = split_line[4]
    except (ValueError, IndexError):
        if line_number > header:
            print(f'bad active_strings field')
        return None
    return dict(runNumber=runNumber, durationSeconds=duration, filePath=path, date=date, activeStrings=n_active)


def parse_runinfo_file(fname, n_active_strings):
    good_runs = []
    total_duration = 0.
    with open(fname) as infile:
        for i, line in enumerate(infile):
            if line == '':
                break
            result = parse_runinfo_line(line, i)
            if result is None:
                continue
            if int(result['activeStrings']) < n_active_strings:
                continue
            total_duration += result['durationSeconds']
            good_runs.append(result)
    return total_duration, good_runs


def get_year_file_list(year):
    i = years.index(year)
    season = seasons[i]
    subfolder = subfolders[i]
    fname = base_path + year + '/filtered/' + subfolder + '/' + season + '_' + runinfo_fname_postfix
    print(fname)
    total_duration, good_runs = parse_runinfo_file(fname, active_strings[i])
    print(f'number of runs: {len(good_runs)}')
    print(f'total duration: {total_duration} seconds  {total_duration / (3600.*24):.2f} days')

    all_input_files = []
    for run_info in good_runs:
        if args.run is not None and run_info['runNumber'] != args.run:
            continue
        if run_info['runNumber'] > run_max:
            continue
        inputPathName = run_info['filePath']
        gcdFilename = glob.glob(inputPathName + '/*%08u*_GCD.i3.*' % run_info['runNumber'])[0]
        if subfolder == 'level2':
            pattern = inputPathName + '/Level2_*_Run%08u_Subrun*.i3.zst' % run_info['runNumber']
        else:
            pattern = inputPathName + '/Level2pass2_*_Run%08u_Subrun*.i3.zst' % run_info['runNumber']
        input_files = glob.glob(pattern)
        if input_files:
            all_input_files.append(gcdFilename)
            all_input_files.extend(input_files)
    return all_input_files


if args.input is None:
    input_files = get_year_file_list(args.year)
else:
    data_files = sorted(glob.glob(args.input))
    if args.max_files is not None:
        data_files = data_files[:args.max_files]
    input_files = [args.gcd] + data_files

print(f'Processing {len(input_files) - 1} data file(s)')


def phys(f):
    def ff(frame):
        if frame.Stop == icetray.I3Frame.Physics:
            return f(frame)
        return True
    return ff


pulses = 'SplitInIcePulses'

tray = I3Tray()
tray.AddModule('I3Reader', FilenameList=input_files,
               SkipKeys=['VHESelfVeto', 'VHEInnerSelfVeto', 'VHESelfVetoVertexTime',
                         'VHESelfVetoVertexPos', 'QTot', 'CausalQTot', 'HLCPulses',
                         'MuonTag', 'MuonTagTime', 'MuonTagPos'])


def renamepulses(fr):
    if 'SplitOfflinePulses' in fr and 'SplitInIcePulses' not in fr:
        fr['SplitInIcePulses'] = fr['SplitOfflinePulses']

tray.AddModule(renamepulses)


def cleanup(frame):
    cleanup_keys = [
        'HLCPulses', 'MuonTag', 'MuonTagTime', 'MuonTagPos',
        'VHEFullSelfVeto', 'VHEFullSelfVetoTime', 'VHEFullSelfVetoPos',
        'I3ShrunkenGeometry', 'HLCPulsesTrimmed', 'CausalQTot',
        'InteriorCausalQTot', 'SplitInIcePulsesTrimmed', 'Primary',
    ]
    for k in cleanup_keys:
        if k in frame.keys():
            del frame[k]

tray.AddModule(cleanup)

physics_uid = 0

@phys
def puid(frame):
    global physics_uid
    frame['PUID'] = icetray.I3Bool(physics_uid)
    physics_uid += 1

tray.Add(puid)


def primary(fr):
    if 'I3MCTree' in fr:
        fr['Primary'] = fr['I3MCTree'].most_energetic_primary

tray.AddModule(primary, Streams=[icetray.I3Frame.DAQ])
tray.AddModule(lambda fr: fr['I3EventHeader'].sub_event_stream == 'InIceSplit')
tray.AddModule('HomogenizedQTot', Pulses=pulses, Output='QTot')
tray.AddModule(phys(lambda fr: fr['QTot'].value > 1000))
tray.AddModule('I3LCPulseCleaning', OutputHLC='HLCPulses', OutputSLC='', Input=pulses)
tray.AddModule('VHESelfVeto', Pulses='HLCPulses', TopBoundaryWidth=60, BottomBoundaryWidth=10,
               DustLayer=-10000, OutputBool='MuonTag', OutputVertexTime='MuonTagTime',
               OutputVertexPos='MuonTagPos')
tray.AddModule('VHESelfVeto', Pulses='HLCPulses', OutputBool='VHEFullSelfVeto',
               OutputVertexTime='VHEFullSelfVetoTime', OutputVertexPos='VHEFullSelfVetoPos')

tray.AddModule('DetectorShrinker', Pulses=pulses, OutPulses=pulses + 'Trimmed',
               TopBoundaryWidth=90, BottomBoundaryWidth=10, OutGeometry='I3ShrunkenGeometry')
tray.AddModule('I3LCPulseCleaning', OutputHLC='HLCPulsesTrimmed', OutputSLC='',
               Input=pulses + 'Trimmed')
tray.AddModule('VHESelfVeto', Pulses='HLCPulsesTrimmed', Geometry='I3ShrunkenGeometry',
               OutputBool='VHEInnerSelfVeto')
tray.AddModule('HomogenizedQTot', Pulses=pulses, Output='CausalQTot', VertexTime='MuonTagTime')
tray.AddModule('HomogenizedQTot', Pulses='HLCPulsesTrimmed', Output='InteriorCausalQTot',
               VertexTime='MuonTagTime')

n_cut = 0

def add_cut(tray, func, name=None):
    global n_cut
    if name is None:
        name = 'Cut' + str(n_cut)
    n_cut += 1

    @phys
    def f(frame):
        frame[name] = icetray.I3Bool(func(frame))

    def cut(frame):
        return frame[name].value

    def remove(frame):
        del frame[name]

    tray.Add(f)
    tray.AddSegment(hdfwriter.I3HDFWriter,
                    Output=args.outdir + '/' + args.output_prefix + '_' + name + '.h5',
                    Keys=['PUID', name], SubEventStreams=['InIceSplit'])
    tray.Add(cut)
    tray.Add(remove)
    return f


def mt_cut_0(frame): return 'MuonTag' in frame.keys()
def mt_cut_1(frame): return frame['MuonTag'].value
def mt_cut_2(frame): return 'VHEInnerSelfVeto' in frame.keys()
def mt_cut_3(frame): return not frame['VHEInnerSelfVeto'].value
def mt_cut_4(frame): return frame['CausalQTot'].value > 6000


@phys
def printme(frame):
    print()
    print(frame['I3EventHeader'].run_id, frame['I3EventHeader'].event_id)
    for name in ['MuonTag', 'VHEFullSelfVeto', 'VHEInnerSelfVeto', 'CausalQTot', 'InteriorCausalQTot']:
        print(name, frame[name] if name in frame else 'None')


add_cut(tray, mt_cut_0, '0_MuonTagExists')
add_cut(tray, mt_cut_1, '1_MuonTagPasses')
add_cut(tray, mt_cut_2, '2_VHEInnerSelfVetoExists')
add_cut(tray, mt_cut_3, '3_VHEInnerSelfVetoPasses')
add_cut(tray, mt_cut_4, '4_CausalQTotPasses')
tray.Add(printme)

count = 0

def counter(frame):
    if frame.Stop != icetray.I3Frame.Physics:
        return
    global count
    count += 1

tray.AddModule(counter)

tray.AddSegment(hdfwriter.I3HDFWriter,
                Output=args.outdir + '/' + args.output_prefix + '.h5',
                Keys=['I3EventHeader', 'MuonTag', 'MuonTagTime', 'VHESelfVeto',
                      'VHESelfVetoVertexTime', 'VHESelfVetoVertexPos', 'QTot',
                      'CausalQTot', 'InteriorCausalQTot', 'VHEFullSelfVeto',
                      'VHEFullSelfVetoPos', 'Primary'],
                SubEventStreams=['InIceSplit'])

tray.Execute()
tray.Finish()
print('count', count)
