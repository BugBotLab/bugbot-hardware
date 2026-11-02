# Change key parameters one at a time, recompute the whole robot, report any feature that fails, restore.
from fusionflow import params as P, helpers as H
doc = App.getDocument("BugBot_Base")
bodies = [o for o in doc.Objects if o.isDerivedFrom("PartDesign::Body")]
def vol(): return round(sum(b.Shape.Volume for b in bodies), 1)
base = vol(); out = {"base_volume": base}
for name, val, back in (("body_r", "42 mm", "40 mm"), ("pcb_z", "31 mm", "29 mm"), ("ball_x", "43 mm", "41.5 mm"),
                        ("wheel_ang1", "50 deg", "40 deg"), ("mast_x", "22 mm", "21 mm"), ("dome_d", "32 mm", "30 mm"),
                        ("sol_dy", "3.5 mm", "2.8 mm"), ("hoop_y", "23 mm", "22.5 mm"), ("grip_ang", "105 deg", "0 deg")):
    P.set_param(name, val); bad = H.recompute(doc)
    out[f"{name}={val}"] = {"failed": bad, "volume": vol()}
    P.set_param(name, back)
bad = H.recompute(doc)
out["restored"] = {"failed": bad, "volume": vol(), "same": abs(vol() - base) < 0.05}
doc.save()
result = out
