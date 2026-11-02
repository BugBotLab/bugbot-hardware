"""Datasheet numbers for every part the stack simulation models, and the
operating limits each scenario is checked against.

Two kinds of number per part:
  model   - what the behavioural subcircuit in stack_models.lib is built from
  limits  - recommended operating range and absolute maximum, from the same
            datasheet, that sim_stack.py checks the simulated stresses against
Every entry names its source document and table/section so a number can be
verified in a minute. "TBC" marks a value taken from memory that still needs
the datasheet page confirmed before the boards are ordered.

Jerome, 2026-09-04: "as accurate as possible, within documented operating
spec, with the ability to change their operation (motors on/off, different
motor types)". Motor types live at the bottom; each scenario picks one and
sets every motor's state individually.
"""

PARTS = {
    # ------------------------------------------------------------- charger
    "ETA6003": dict(
        source="ETA Semi ETA6003 datasheet V2.7: Pin Configuration p2, Electrical Characteristics p3-4, "
               "Pin Description p4, typical curves p5. CONFIRMED from the PDF 2026-09-04 "
               "(the first entry had VBUS 4.35-6.5 V / 7 V abs max: the real limits are 4.4-5.5 V / 6 V).",
        pinout={"1": "SYS", "2": "IN", "3": "SW", "4": "SW", "5": "PGND", "6": "ENB", "7": "NTC",
                "8": "ENPPB", "9": "STATS", "10": "GND", "11": "ISET1", "12": "ISET2", "13": "USB_DET",
                "14": "BATT", "15": "SYS", "16": "BATT", "17": "EP"},
        model=dict(vbus_uvlo=3.9, vbus_uvlo_hys=0.5, vhold=4.5,                 # input DPPM: current limit folds back below 4.5 V
                   sys_min=3.6, sys_max=4.5, sys_track=0.17,                   # SYS = clamp(VBAT + 0.17, 3.6, 4.5) (curve p5)
                   path_ron=0.050, hs_ron=0.100, ls_ron=0.060, f_sw=3e6, hs_ilim=3.5,
                   ichg_k=1000.0,                                              # I_chg = 1 V * 1000 / R_ISET1 (USB_DET low)
                   vterm=4.2, vterm_range=(4.16, 4.24), v_precond=2.9, i_precond=0.10, eoc_frac=0.10,
                   restart_mv=150, ntc_cold=0.765, ntc_hot=0.35, ntc_hys=0.015,
                   enb_active_low=True, enppb_gnd_enables_path=True, usb_det_low_selects_iset1=True,
                   stats_iol=0.010, sys_uvlo=2.25, tsd=160),
        limits=dict(vbus=(4.4, 5.5), vbus_absmax=6.0, batt_absmax=6.0, ichg_max=2.5, isys_max=3.5,
                    tj_max=125, theta_ja=50),
    ),
    # ---------------------------------------------------------- buck-boost
    "TPS63020": dict(
        source="TI SLVS916I (Oct 2019): Pin Functions p4, 6.1/6.3/6.5 p5-6, Fig 1 p7. CONFIRMED from the PDF 2026-09-04.",
        pinout={"1": "VINA", "2": "GND", "3": "FB", "4": "VOUT", "5": "VOUT", "6": "L2", "7": "L2",
                "8": "L1", "9": "L1", "10": "VIN", "11": "VIN", "12": "EN", "13": "PS/SYNC", "14": "PG", "15": "PGND (pad)"},
        model=dict(vfb=0.5, vfb_range=(0.495, 0.505), en_vih=1.2, en_vil=0.4, vin_min=1.8, uvlo_vina=1.5,
                   eff=0.90, f_sw=2.4e6, f_range=(2.2e6, 2.6e6), ron=0.050, iq=25e-6, ishdn=0.1e-6,
                   iout_max_vin_gt_2v5=2.0, isw_lim=(3.5, 4.0, 4.5), ovp_out=5.5, otp=140,
                   ps_sync_high_disables_power_save=True, pg_open_drain=True),
        limits=dict(vin=(1.8, 5.5), vin_absmax=7.0, vout=(1.2, 5.5), iout=2.0, isw_peak=3.5,
                    tj_max=125, theta_ja=41.8),
    ),
    # --------------------------------------------------------- motor driver
    "DRV8830": dict(
        source="TI SLVSAB2F (DRV8830, Feb 2012): Table 1 terminal functions, Electrical "
               "Characteristics p5, Current Limit / Protection Circuits p11, register map p13. "
               "CONFIRMED 2026-09-04 from the PDF.",
        # DGQ (MSOP-10) pin table, TOP VIEW: pin 1 is OUT2, not OUT1, and VCC/GND,
        # SCL/SDA and A0/A1 are all on different pins from the first guess. The
        # Motion board was generated from the wrong table (see gen_symbols_motion.py)
        # and must be corrected before fab.
        pinout={"1": "OUT2", "2": "ISENSE", "3": "OUT1", "4": "VCC", "5": "GND", "6": "nFAULT",
                "7": "A0", "8": "A1", "9": "SDA", "10": "SCL", "11": "GND (PowerPAD)"},
        # I2C 7-bit address from (A1, A0): 0 = GND, Z = open, 1 = VCC
        addresses={("0", "0"): 0x60, ("0", "Z"): 0x61, ("0", "1"): 0x62, ("Z", "0"): 0x63,
                   ("Z", "Z"): 0x64, ("Z", "1"): 0x65, ("1", "0"): 0x66, ("1", "Z"): 0x67, ("1", "1"): 0x68},
        model=dict(ron_total=0.45, ron_total_max=0.72,          # HS 250 + LS 200 mOhm typ (400+320 max at 85 C)
                   vsense_trip=0.2, vsense_trip_range=(0.16, 0.24),
                   ilim_engage_us=3, ilim_fault_ms=275,          # duty cut after ~3 us; FAULTn/ILIMIT bit after ~275 ms
                   ocp=(1.3, 3.0), ocp_deglitch_us=2,            # OCP latches all FETs off until CLEAR
                   uvlo_rise=(2.575, 2.75), uvlo_fall=2.47,      # typ/max rising, typ falling
                   soft_ramp_ms=12,                              # standby -> 100 % duty takes up to 12 ms
                   pwm_hz=44.5e3, vref=1.285,
                   vset_min=0.48, vset_max=5.06, vset_step=0.08,   # V = 4 x 1.285 x (VSET+1) / 64
                   iq_active=1.4e-3, iq_active_max=2e-3, iq_standby=0.3e-6, pin_cap=10e-12,
                   tsd=160),
        limits=dict(vcc=(2.75, 6.8), vcc_absmax=7.0, iout_peak=1.0, iout_rms=1.0,
                    isense_r_max=1.0, isense_v_max=0.5, tj_max=150, theta_ja=69.3),
    ),
    # ------------------------------------------------------------- P-FETs
    "SI2333": dict(
        source="Vishay SI2333DDS S13-2055, Absolute Maximum Ratings + Specifications",
        model=dict(vth=-0.8, rds_4v5=0.023, rds_2v5=0.037, ciss=1270e-12, vsd=0.8),
        limits=dict(vds_absmax=-12.0, vgs_absmax=8.0, id_cont=3.7, id_pulse=15.0, pd_max=1.25),
    ),
    # --------------------------------------------------------------- ESD
    "USBLC6-2SC6": dict(
        source="ST USBLC6-2 datasheet (SOT23-6 pinout 1/6 I/O1, 2 GND, 3/4 I/O2, 5 VBUS; line capacitance "
               "3.5 pF max). Pinout matches KiCad's Power_Protection:USBLC6-2SC6 symbol, 2026-09-04.",
        pinout={"1": "I/O1", "2": "GND", "3": "I/O2", "4": "I/O2", "5": "VBUS", "6": "I/O1"},
        model=dict(cline=3.5e-12, ileak=10e-9),
        limits=dict(vbus=(0, 5.25), line_v=(0, 5.25)),
    ),
    # ------------------------------------------------------------ inductors
    "L2_2u2": dict(   # Sunlord MWSA0402S-2R2MT, LCSC C408335 (JLC part page + DigiKey, 2026-09-04)
        source="Sunlord MWSA-S series datasheet / DigiKey 14120157: 2.2 uH 20 %, Isat 4.0 A typ (5.0 A max), "
               "Irms 3.8 A typ (4.5 A max), DCR 58 mOhm max, 4.4 x 4.2 mm unshielded",
        model=dict(l=2.2e-6, dcr=0.058),
        limits=dict(isat=4.0, irms=3.8),
    ),
    "L1_1uH": dict(   # cjiang FTC252010S1R0MBCA, LCSC C5832356 (LCSC page, 2026-09-04)
        source="LCSC C5832356: 1 uH, rated 4.5 A, Isat 5.3 A, DCR 25 mOhm, 1008 (2.5 x 2.0 mm)",
        model=dict(l=1e-6, dcr=0.025),
        limits=dict(isat=5.3, irms=4.5),
    ),
    # ------------------------------------------------------------ passives
    # LCSC basic-part ratings the BOM actually carries (confirmed on the LCSC pages 2026-09-04)
    "C_22u_0805": dict(source="LCSC C45783 Samsung CL21A226MAQNNNE 22uF 0805 X5R 25V", limits=dict(v_rated=25.0)),
    "C_10u_0805": dict(source="LCSC C15850 Samsung CL21A106KAYNNNE 10uF 0805 X5R 25V", limits=dict(v_rated=25.0)),
    "C_100n_0402": dict(source="LCSC C1525 100nF 0402 X7R 50V", limits=dict(v_rated=50.0)),
    "C_1u_0402": dict(source="LCSC C52923 1uF 0402 X5R 16V", limits=dict(v_rated=16.0)),
    "C_4u7_0603": dict(source="LCSC C19666 Samsung CL10A475KO8NNNC 4.7uF 0603 X5R 16V", limits=dict(v_rated=16.0)),
    "C_22p_0402": dict(source="LCSC C70464 Samsung CL05C220JB5NNNC 22pF 0402 C0G 50V", limits=dict(v_rated=50.0)),
    "CB1_100u": dict(source="LCSC C7196 Kyocera AVX TAJB107M010RNJ 100uF 10V B-case 3528, ESR 1.4 Ohm @100kHz",
                     model=dict(esr=1.4),
                     limits=dict(v_rated=10.0, v_derated=5.0)),   # tantalum: 50 % derating
    "R_0402": dict(source="generic 0402 thick film", limits=dict(p_rated=0.0625)),
    "R_0603": dict(source="generic 0603 thick film", limits=dict(p_rated=0.100)),
    "F1_PTC": dict(source="LCSC C20627123 LUTE 1812L300/24GR: 3 A hold, 5 A trip, 24 V, 40 A max, 10 mOhm, <=4 s trip",
                   model=dict(r_cold=0.010, r_post_trip_max=0.060), limits=dict(i_hold=3.0, i_trip=5.0, v_max=24.0)),
    # --------------------------------------------------------- Vision loads
    "ESP32-P4-Module": dict(
        source="Waveshare ESP32-P4-Module wiki (3.3 V in); Espressif ESP32-P4 datasheet VDD 3.0-3.6 V",
        model=dict(i_typ=0.55, i_peak=0.90),
        limits=dict(v3v3=(3.0, 3.6)),
    ),
    "VL53L5CX": dict(source="ST VL53L5CX datasheet", model=dict(i_typ=0.05), limits=dict(vdd=(2.8, 3.6))),
    "OV5647_head": dict(source="OV5647 module (Pi Zero style), 3.3 V in", model=dict(i_typ=0.15), limits=dict(vdd=(3.0, 3.6))),
    "WS2812B": dict(source="Worldsemi WS2812B datasheet", model=dict(i_max=0.060), limits=dict(vdd=(3.5, 5.3), vdd_practical_min=3.3)),
    # Jerome's pick 2026-09-04: HobbyKing HK-5320 ultra-micro digital servo, 1.7 g,
    # 2.5-4.8 V, 0.05 kg.cm @ 3.7 V / 0.075 kg.cm @ 4.2 V, 0.075 s/60 deg @ 3.7 V
    # (hobbyking.com listing + servodatabase.com). The listing gives no current
    # figures: the ones below are typical for a 1.7 g coreless servo (TBC by
    # measurement: stall it against a finger with a meter in series).
    "servo_1S": dict(source="HobbyKing HK-5320 (hobbyking.com / servodatabase.com listing, 2026-09-04); currents TBC",
                     model=dict(i_idle=0.005, i_move=0.06, i_stall=0.15),
                     limits=dict(v=(2.5, 4.8))),
    # ------------------------------------------------------ Odometry board (2026-09-06)
    "AP2127K-ADJ": dict(
        source="Diodes AP2127 datasheet DS36478: SOT-23-5 pin table (1 VIN, 2 GND, 3 EN, 4 ADJ, 5 VOUT), "
               "Vadj 0.8 V, 300 mA, VIN 2.5-6.0 V, dropout 300 mV at 300 mA, Iq 60 uA. Pin table CONFIRMED "
               "in the 2026-09-06 audit; the divider R1 150k / R2 110k gives 0.8 x (1 + 150/110) = 1.891 V.",
        pinout={"1": "VIN", "2": "GND", "3": "EN", "4": "ADJ", "5": "VOUT"},
        model=dict(vref=0.8, iout=0.3, dropout=0.3, iq=60e-6, en_vih=1.2),
        limits=dict(vin=(2.5, 6.0), vin_absmax=7.0, iout=0.3, pd_max=0.5),
    ),
    "BNO055": dict(
        source="Bosch BST-BNO055-DS000 (rev 1.8): Table 4-1 pin description, section 1.2 electrical "
               "(VDD 2.4-3.6 V, VDDIO 1.7-3.6 V, 12.3 mA typ in NDOF fusion mode), section 4.3 I2C "
               "(PS1=PS0=0 = I2C, COM3 low = address 0x28 / high = 0x29). Pin table CONFIRMED 2026-09-06.",
        pinout={"1": "PIN1", "2": "GND", "3": "VDD", "4": "nBOOT_LOAD_PIN", "5": "PS1", "6": "PS0",
                "7": "PIN7", "8": "PIN8", "9": "CAP", "10": "BL_IND", "11": "nRESET", "12": "PIN12",
                "13": "PIN13", "14": "INT", "15": "PIN15", "16": "PIN16", "17": "COM3", "18": "COM2",
                "19": "COM1", "20": "COM0", "21": "PIN21", "22": "PIN22", "23": "PIN23", "24": "PIN24",
                "25": "GNDIO", "26": "XOUT32", "27": "XIN32", "28": "VDDIO"},
        model=dict(i_ndof=12.3e-3, i_vddio=20e-6, pin_cap=10e-12, addr_com3_low=0x28, addr_com3_high=0x29),
        limits=dict(vdd=(2.4, 3.6), vddio=(1.7, 3.6), v_absmax=4.25),
    ),
    "PMW3360": dict(
        source="PixArt PMW3360DM-T2QU Product Datasheet v1.30 (6 April 2016), public mirror "
               "trackballs.eu/media/Ploopy/Adept/PMW3360DM-T2QU.pdf (copy in BugBot_Odometry_Board/datasheets/). "
               "Table 1 pin description p3; Table 2 abs max p14 (VDD 2.10 V, VDDIO 3.60 V); Table 3 recommended "
               "operating p14 (VDD 1.80-1.90-2.10 V, VDDIO 1.80-3.60 V and >= VDD, supply rise 0.15-20 ms); "
               "Table 4 AC p15-16 (transient supply current 70 mA on VDD / 60 mA on VDDIO during the ramp); "
               "Table 5 DC p16: I_DD run1/2/3/4 = 16.3 / 18.6 / 21.6 / 37.0 mA typ 'average current consumption, "
               "including LED current with 1 ms polling', rest1 2.8 mA, rest2 61 uA, rest3 32 uA, power down 10 uA; "
               "LED current 12 mA at the test condition. CONFIRMED 2026-09-06 (pin table = the alpha-board symbol).",
        pinout={"1": "NC", "2": "NC", "3": "VDDPIX", "4": "VDD", "5": "VDDIO", "6": "NC", "7": "NRESET",
                "8": "GND", "9": "MOTION", "10": "SCLK", "11": "MOSI", "12": "MISO", "13": "NCS",
                "14": "NC", "15": "LED_P", "16": "NC"},
        # run4 = the highest frame-rate mode, LED included: 37 mA from the 1.9 V rail, split
        # here as 25 mA core + 12 mA LED (LED_P), VDDIO current is not specified (1 mA allowance)
        model=dict(i_run=25e-3, i_led=12e-3, i_vddio=1e-3, i_run_modes=(16.3e-3, 18.6e-3, 21.6e-3, 37.0e-3),
                   i_rest=(2.8e-3, 61e-6, 32e-6), i_pd=10e-6, i_ramp_vdd=70e-3, i_ramp_vddio=60e-3,
                   t_rise=(0.15e-3, 20e-3), c_in=50e-12),
        limits=dict(vdd=(1.8, 2.1), vdd_absmax=2.10, vddio=(1.8, 3.6), vddio_absmax=3.6, vin_absmax=3.6, t_a=(0, 40)),
    ),
    "VL53L5CX_addr": dict(source="ST VL53L5CX: default I2C address 0x29 (7-bit)", model=dict(addr=0x29)),
}

# ------------------------------------------------------------ motor types
# Coreless / brushed DC motors the robot may be fitted with. The DC model is
# R (winding), back-EMF per krpm (kV), no-load speed at 3 V, stall current at
# 3 V (= 3/R), and how the harness expresses "running": VBEMF = kv * rpm.
# Sources: typical vendor listings for these sizes; measure the real motor's
# winding resistance with a meter and put it here (TBC until then).
# Mechanical numbers for the transient (MOTOR_MECH): rotor inertia j (kg m2),
# viscous friction b (N m s/rad), constant load torque t_load (N m) and the
# eccentric weight for a vibration drive as extra inertia. The 6 mm rotor is
# ~0.3 g at r 2.5 mm -> J ~ 1e-9; a 1 g eccentric weight at 3 mm adds ~9e-9.
# no-load current = b * w_noload / KE, so b is set from i_noload (TBC).
MOTOR_TYPES = {
    "0615_coreless": dict(source="6x15 mm coreless, 3 V class (typical listing, TBC by measurement)",
                          r=4.0, l=20e-6, kv_v_per_krpm=0.135, rpm_noload_3v=21000, i_noload=0.045, i_stall_3v=0.75,
                          j=1.0e-8, b=2.6e-8, t_load=1.0e-5),
    # the drone-type 615 (Eachine/Inductrix class) is a different animal: vendor
    # listings 2026-09-04 give 3.7 V rated, 50-60 krpm, 42-71 mA no-load, 1.9 A
    # locked rotor -> R ~ 2 Ohm. Its stall current is 4x the 400 mA ISENSE limit,
    # so the limiter, not the winding, sets the stall current. Measure the real
    # motor's R with a meter and pick the type that matches.
    "0615_drone_3v7": dict(source="615 drone motor listings (Amazon B0DCWC2F6Y / xyzhobby / nfpmotor D0615), TBC by measurement",
                           r=1.95, l=12e-6, kv_v_per_krpm=0.062, rpm_noload_3v=44000, i_noload=0.060, i_stall_3v=1.5,
                           j=1.0e-8, b=1.4e-8, t_load=1.0e-5),
    "0716_coreless": dict(source="7x16 mm coreless, 3.7 V class (typical, TBC)",
                          r=2.5, l=15e-6, kv_v_per_krpm=0.16, rpm_noload_3v=18000, i_noload=0.07, i_stall_3v=1.2,
                          j=1.6e-8, b=5.7e-8, t_load=2.0e-5),
    "N20_geared_3v": dict(source="N20 3 V geared, 100:1 (typical, TBC); inertia/load referred to the motor shaft",
                          r=6.0, l=250e-6, kv_v_per_krpm=0.2, rpm_noload_3v=13000, i_noload=0.04, i_stall_3v=0.5,
                          j=3.0e-8, b=5.6e-8, t_load=3.0e-5),
}


def motor_bemf(mtype, load_frac):
    """Back-EMF for a motor of `mtype` at the drive voltage, running at
    (1 - load_frac) of no-load speed: 0 = free-running, 1 = stalled."""
    m = MOTOR_TYPES[mtype]
    rpm = m["rpm_noload_3v"] * (1.0 - load_frac)
    return round(m["kv_v_per_krpm"] * rpm / 1000.0, 3)
