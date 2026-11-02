# Beetle – parts that differ from the BugBot (Scorpion)

The Beetle is the shared base robot with a passive front shield in place of the gripper arms, the front bar and the kicker.
Everything else is in `PARTS.md`. Model: `BugBot_Beetle.FCStd`, built by `build_beetle.py`. Approved 2D:
`sketches/beetle_shield_v2c.png`. The front is a sasumata-style U, held by two flush bolts.
The shield is modelled from plain boxes and cylinders with real fillets: r3 on the outside corners, r2 on the inside corners,
r1 under the pads. The U's middle block is flush with the foot plates: same front (x 47.5), same top (z 25.5) and the same
r3 corner.

## Left off (compared with the Scorpion)
- Gripper hoop arms, front bar, TPU sleeve, bar screw and nut.
- Kicker: JF-0520B solenoid, kick disc, kicker bracket and its screws. The kicker charger parts on the main board can stay unfitted.

The SG90 servo, its horn, the pivot bracket and the pivot bushing **stay**: the shield plates mount on them. The servo isn't powered.

## Printed parts

| Part | What it does | Size (mm) | Material | Qty |
|---|---|---|---|---|
| ShieldPlateL | +Y side plate: the hoop arm's pivot end (horn pad), a straight top bar, a foot resting on the main board, a leg down past the wall, ending in a foot plate (5.5 wide, 3.5 elsewhere; up to z 25.5, to x 47.5) with **2 hex pockets for the nuts** | ≈ 46 × 40 × 3.5 / 5.5 (pivot end as the hoop arm) | PETG, 100 % infill | 1 |
| ShieldPlateR | −Y side plate: the same, with the hoop arm's pivot end (bushing), and **2 counterbores (Ø6.0 × 3.2) for the screw heads** | ≈ 46 × 40 × 3.5 / 5.5 | PETG, 100 % infill | 1 |
| Shield U front | One part: a middle block between the foot plates (x 38–50, up to z 25.5, behind the stinger's reach), running into a low U (z 7.5–13; inside R21, 6 thick; a 40 mm ball fits). Short prongs flared 20° with round tips; the tips are 35 mm ahead of the body | ≈ 38 × 60 × 18 | PETG | 1 |

Print the plates flat, inner face down, like the hoop arms. Print the U front on its bottom face, with no supports. The block is a plain rise and the bolt holes run sideways; the holes' tops bridge 3.5 mm.

## Fasteners

| Where | Fastener | Qty |
|---|---|---|
| U front to both plates: foot plate R, U middle block, foot plate L, at (x 42.5, z 12) and (x 42.5, z 21) | **M3 × 50 socket head, DIN 912** + **M3 nut, DIN 934**, plus a drop of medium threadlocker. Heads sunk in the −Y foot plate, nuts in hex pockets (5.8 AF × 2.6) in the +Y foot plate. Each screw ends 0.1 short of the nut's outer face and 0.3 inside the plate face: nothing sticks out. Ø3.5 holes | 2 + 2 |
| −Y plate on the pivot bracket and bushing | M2 × 8 + M2 nyloc (the gripper's pivot axle). Tighten fully: nothing swings | 1 + 1 |
| +Y plate to the servo horn | M1.4 × 4 self-tapping (the horn's own 2 screws) | 2 |
| Pivot bracket, from under the board | M2 × 6 self-tapping (the servo mount module, as on the Scorpion) | 2 |

## Fits (worst-case printer)
- U front to the foot plates: 0.25 a side; the two bolts clamp them together. With two bolts one above the other, the U can't pivot down and drag.
- Walls round the counterbores and hex pockets: at least 1.15 mm.
- U middle block to the Beetle's chassis: 0.79.
- Legs to the chassis wall and the board edge: 0.42 at the closest point.
- The feet rest on the board top (z 30.51). Gravity holds them down; if something lifts the blade, the shield rises and drops back.

## Function
- A Wasp that drives in head-on is caught on the prong tips. Its fired stinger then ends **20 mm** short of the Beetle's body. This is the worst case from model numbers: Wasp wall r 40.6, fired ram face at 47.0, with its base-plate lip ignored.
- Off-centre, the U's curve centres a Wasp. At 45 mm off, its stinger still ends about 30 mm from the Beetle's body.
- A 40 mm ball fits in the U, so the Beetle can cradle and push it.
- Only the front is shielded.
- Assembly order:
  1. Fit both plates on the robot (horn screws, then the pivot axle).
  2. Drop the 2 nuts into the hex pockets in the +Y foot plate (a dab of glue or tape holds them).
  3. Slide the U's middle block in between the foot plates from the front.
  4. Push the 2 M3 × 50 through from the −Y side (2.5 mm hex key), with threadlocker, and tighten.
