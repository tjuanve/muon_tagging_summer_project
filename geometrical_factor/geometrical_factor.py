from icecube import phys_services
from icecube import MuonGun

# Ignoring zenith dependance
relative_area_no = phys_services.Cylinder(1020, 550).acceptance(0, 1) / phys_services.Cylinder(900, 420).acceptance(0, 1)
print(f"Relative area, ignoring flux dependance on zenith angle     :{relative_area_no}")

# With zenith dependance
full_cylinder = MuonGun.Cylinder(1020, 550)
shrunk_cylinder = MuonGun.Cylinder(900, 420)
model = MuonGun.load_model('GaisserH4a_atmod12_SIBYLL')
relative_area_yes = full_cylinder.integrate_flux(model.flux) / shrunk_cylinder.integrate_flux(model.flux)
print(f"Relative area, considering flux dependance on zenith angle  :{relative_area_yes}")

# ── ExtrudedPolygon from actual GCD ───────────────────────────────────────────
from icecube import icetray, dataio

I3FILE = '/data/user/tvaneede/muon_tagging/event_selection/output/IC86_2021_selected.i3.zst'

geo_full = None
geo_trim = None
f = dataio.I3File(I3FILE)
while f.more():
    frame = f.pop_frame()
    if frame.Stop == icetray.I3Frame.Geometry and geo_full is None:
        geo_full = frame['I3Geometry']
    if frame.Stop == icetray.I3Frame.Physics and geo_trim is None and 'I3GeometryTrimmed' in frame:
        geo_trim = frame['I3GeometryTrimmed']
    if geo_full is not None and geo_trim is not None:
        break

from icecube import dataclasses

def geo_to_positions(geo):
    return [omgeo.position for omkey in geo.omgeo.keys()
            for omgeo in [geo.omgeo[omkey]]
            if omgeo.omtype == dataclasses.I3OMGeo.IceCube]

full_poly   = MuonGun.ExtrudedPolygon(geo_to_positions(geo_full), 0.)
shrunk_poly = MuonGun.ExtrudedPolygon(geo_to_positions(geo_trim), 0.)

# Ignoring zenith dependance
relative_area_poly_no = full_poly.acceptance(0, 1) / shrunk_poly.acceptance(0, 1)
print(f"ExtrudedPolygon, ignoring flux dependance on zenith angle   :{relative_area_poly_no}")

# With zenith dependance
relative_area_poly_yes = full_poly.integrate_flux(model.flux) / shrunk_poly.integrate_flux(model.flux)
print(f"ExtrudedPolygon, considering flux dependance on zenith angle:{relative_area_poly_yes}")
