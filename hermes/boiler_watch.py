#!/home/rapple/.hermes/hermes-agent/venv/bin/python
"""Boiler watcher (Jonah / Telegram channel).  Silent unless there is something to say.

Reads the same Home Assistant entities the ESPHome device publishes and prints a message
(cron delivers stdout to Telegram) for:
  LOW      binary_sensor.basement_boiler_temperature_low  -> immediately, then every 60 min until cleared or paused
  HIGH     binary_sensor.basement_boiler_temperature_high -> once per episode
  OFFLINE  sensor.basement_boiler_water_temperature unavailable/unknown for >= 10 min -> once per episode
  NORMAL   alert cleared -> once
Pause: input_boolean.boiler_alerts_paused (ON = no repeat LOW messages; clears itself on recovery in HA).
The 10-minute LOW delay lives in the ESPHome device, so this script does not add a second delay.
If the boiler entities do not exist yet (device not deployed) it stays silent.

  boiler_watch.py            normal run (cron)
  boiler_watch.py --selftest simulate scenarios, no network, no state writes
"""
import json, os, sys, time, urllib.request, urllib.error

HA = os.environ.get("HASS_URL", "http://192.168.1.71:8123")
STATE = os.path.expanduser("~/.hermes/state/boiler_watch.json")
REPEAT_S, OFFLINE_S = 3600, 600
E = {"temp": "sensor.basement_boiler_water_temperature", "low": "binary_sensor.basement_boiler_temperature_low",
     "high": "binary_sensor.basement_boiler_temperature_high", "paused": "input_boolean.boiler_alerts_paused"}


def decide(st, snap, now):
    """Pure decision function. st = persisted dict, snap = {key: state string or None(missing)}.
    Returns (messages, new_state)."""
    st = dict(st); msgs = []
    temp, low, high, paused = snap["temp"], snap["low"], snap["high"], snap["paused"]
    t = None
    try: t = float(temp)
    except (TypeError, ValueError): pass
    shown = f"{t:.1f}°F" if t is not None else "no reading"
    is_paused = paused == "on"

    # LOW
    if low == "on":
        if not is_paused and now - st.get("low_last", 0) >= REPEAT_S:
            n = st.get("low_count", 0) + 1
            msgs.append(f"🥶 BOILER LOW: water is {shown} (alert below 140°F)."
                        + (f" Reminder #{n - 1}." if n > 1 else "")
                        + " Repeats hourly until it recovers. Say 'pause boiler alerts' to stop reminders.")
            st["low_last"], st["low_count"] = now, n
        st["low_active"] = True
    elif low == "off" and st.get("low_active"):
        st.update(low_active=False, low_last=0, low_count=0)
        st["recovered"] = True

    # HIGH
    if high == "on":
        if not st.get("high_active"):
            msgs.append(f"🔥 BOILER HIGH: water is {shown} (alert above 190°F). Check it now.")
            st["high_active"] = True
    elif high == "off" and st.get("high_active"):
        st["high_active"], st["recovered"] = False, True

    # OFFLINE (no usable reading)
    if t is None and temp is not None or temp in ("unavailable", "unknown"):
        st.setdefault("offline_since", now)
        if now - st["offline_since"] >= OFFLINE_S and not st.get("offline_sent"):
            msgs.append("⚠️ BOILER SENSOR OFFLINE: no temperature reading for 10+ minutes. "
                        "The boiler is NOT being monitored. Check probe wiring, device power and WiFi.")
            st["offline_sent"] = True
    else:
        if st.get("offline_sent"): msgs.append(f"✅ Boiler sensor back online ({shown}).")
        st.pop("offline_since", None); st["offline_sent"] = False

    # NORMAL
    if st.get("recovered") and low != "on" and high != "on":
        msgs.append(f"✅ Boiler back to normal: {shown}.")
        st["recovered"] = False
    return msgs, st


def fetch(token):
    snap = {}
    for k, ent in E.items():
        req = urllib.request.Request(f"{HA}/api/states/{ent}", headers={"Authorization": f"Bearer {token}"})
        try:
            snap[k] = json.load(urllib.request.urlopen(req, timeout=15))["state"]
        except urllib.error.HTTPError as e:
            if e.code == 404: snap[k] = None  # entity does not exist (yet)
            else: raise
    return snap


def selftest():
    ok = True
    def chk(name, cond):
        nonlocal ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name)
    s, T0 = {}, 1_000_000
    base = dict(temp="150.0", low="off", high="off", paused="off")
    m, s = decide(s, {**base, "temp": "135.2", "low": "on"}, T0);           chk("low: first alert fires", len(m) == 1 and "LOW" in m[0])
    m, s = decide(s, {**base, "temp": "134.0", "low": "on"}, T0 + 600);     chk("low: silent at +10min", m == [])
    m, s = decide(s, {**base, "temp": "133.0", "low": "on"}, T0 + 3599);    chk("low: silent at +59:59", m == [])
    m, s = decide(s, {**base, "temp": "133.0", "low": "on"}, T0 + 3600);    chk("low: repeats at +60min", len(m) == 1 and "Reminder #1" in m[0])
    m, s = decide(s, {**base, "temp": "133.0", "low": "on", "paused": "on"}, T0 + 7200); chk("low: paused -> no repeat", m == [])
    m, s = decide(s, {**base, "temp": "133.0", "low": "on", "paused": "on"}, T0 + 99999); chk("low: still paused much later", m == [])
    m, s = decide(s, {**base, "temp": "150.0", "low": "off"}, T0 + 100000); chk("recovery: one 'back to normal'", len(m) == 1 and "normal" in m[0])
    m, s = decide(s, {**base}, T0 + 100100);                                chk("recovery: then silent", m == [])
    m, s = decide(s, {**base, "temp": "133.0", "low": "on"}, T0 + 200000);  chk("new episode alerts again", len(m) == 1 and "LOW" in m[0])
    s2 = {}
    m, s2 = decide(s2, {**base, "temp": "195.0", "high": "on"}, T0);        chk("high: fires once", len(m) == 1 and "HIGH" in m[0])
    m, s2 = decide(s2, {**base, "temp": "196.0", "high": "on"}, T0 + 3600); chk("high: no repeat", m == [])
    m, s2 = decide(s2, {**base, "temp": "180.0", "high": "off"}, T0 + 4000); chk("high: clears to normal", len(m) == 1 and "normal" in m[0])
    s3 = {}
    m, s3 = decide(s3, {**base, "temp": "unavailable"}, T0);                chk("offline: not yet at 0 min", m == [])
    m, s3 = decide(s3, {**base, "temp": "unavailable"}, T0 + 599);          chk("offline: not yet at 9:59", m == [])
    m, s3 = decide(s3, {**base, "temp": "unavailable"}, T0 + 600);          chk("offline: fires at 10min", len(m) == 1 and "OFFLINE" in m[0])
    m, s3 = decide(s3, {**base, "temp": "unavailable"}, T0 + 1200);         chk("offline: only once", m == [])
    m, s3 = decide(s3, {**base, "temp": "160.0"}, T0 + 1300);               chk("offline: back online msg", len(m) == 1 and "online" in m[0])
    m, _ = decide({}, {"temp": None, "low": None, "high": None, "paused": None}, T0); chk("not deployed (entities missing): silent", m == [])
    m, _ = decide({}, {**base, "temp": "unknown"}, T0);                     chk("blip 'unknown' alone: silent", m == [])
    print("ALL PASS" if ok else "SOME FAILED"); return 0 if ok else 1


def main():
    if "--selftest" in sys.argv: sys.exit(selftest())
    token = os.environ.get("HASS_TOKEN")
    if not token:
        for line in open(os.path.expanduser("~/.hermes/.env")):
            if line.startswith("HASS_TOKEN="): token = line.split("=", 1)[1].strip().strip('"\'')
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    try:
        snap = fetch(token)
    except Exception as e:
        # HA unreachable: count failures, say something only after ~10 minutes of it (5 runs @ 2 min)
        st["ha_fail"] = st.get("ha_fail", 0) + 1
        if st["ha_fail"] == 5: print(f"⚠️ Boiler watcher cannot reach Home Assistant ({str(e)[:60]}). Boiler monitoring is blind.")
        json.dump(st, open(STATE, "w")); return
    st["ha_fail"] = 0
    if snap["temp"] is None and snap["low"] is None:  # device not deployed yet
        return
    msgs, st = decide(st, snap, time.time())
    json.dump(st, open(STATE, "w"))
    for m in msgs: print(m)


if __name__ == "__main__":
    main()
