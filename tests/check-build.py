"""Post-build oracle: python tests/check-build.py BUILD_DIR ORIGINAL_BT_CPP."""
import json
from pathlib import Path
import shlex
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "scripts"))
from bluetooth import adapt

build = Path(sys.argv[1]).resolve()
original = Path(sys.argv[2]).resolve()
settings = json.loads((build / "config/sdkconfig.json").read_text())
assert settings["BT_SSP_ENABLED"] is False
assert settings["BT_SPP_ENABLED"] and settings["BT_CLASSIC_ENABLED"]
assert settings["AUTOSTART_ARDUINO"] and settings["FREERTOS_HZ"] == 1000
commands = json.loads((build / "compile_commands.json").read_text())
bt = [Path(c["file"]) for c in commands if c["file"].endswith("/BluetoothSerial.cpp")]
assert bt == [build / "rcdev/BluetoothSerial.cpp"] or bt == [build / "devrabit/BluetoothSerial.cpp"], bt
assert bt[0].read_text() == adapt(original.read_text())
text = bt[0].read_text()
assert "ESP_SPP_SEC_AUTHENTICATE | ESP_SPP_SEC_ENCRYPT" in text
assert 'strcmp(pin, "1234")' not in text
assert 'if (!pin || strlen(pin) != 4)' in text
assert "pin[i] < '0' || pin[i] > '9'" in text
assert "case ESP_BT_GAP_CFM_REQ_EVT:" not in text
assert text.index("if (!_isPinSet || _pin_len != 4 || !btSetPin())") < text.index("if (esp_spp_init(")
try:
    adapt(original.read_text().replace("esp_spp_start_srv(ESP_SPP_SEC_NONE,", "esp_spp_start_srv(CHANGED,"))
except ValueError:
    pass
else:
    raise AssertionError("Must reject unexpected upstream")
# Run the exact generated input-validation statements on the host.
validation = text[text.index('    if (!pin || strlen(pin) != 4)'):]
# Only the first two statements are the RCDEV PIN policy.
validation = '\n'.join(validation.splitlines()[:2])
source = '#include <cstring>\n#include <cassert>\nbool valid(const char* pin) {\n' + validation + '\nreturn true; }\nint main(){ assert(valid("1234")); assert(valid("5678")); assert(valid("0000")); assert(!valid(nullptr)); assert(!valid("123")); assert(!valid("12345")); assert(!valid("abcd")); }\n'
cpp = build / "pin-policy.cpp"
cpp.write_text(source)
subprocess.run(["g++", "-Wall", "-Wextra", "-Werror", str(cpp), "-o", str(build / "pin-policy")], check=True)
subprocess.run([str(build / "pin-policy")], check=True)
# Ask the SDK compiler, not only the defaults file.
cmd = next(c for c in commands if c["file"].endswith("/btc_gap_bt.c"))
args = shlex.split(cmd["command"])
pos = args.index("-o")
del args[pos:pos + 2]
args.remove("-c")
result = subprocess.run(args + ["-dM", "-E"], cwd=build, check=True, capture_output=True, text=True)
assert "#define CONFIG_BT_SSP_ENABLED" not in result.stdout
assert "#define BT_SSP_INCLUDED FALSE" in result.stdout
assert "#define CONFIG_BT_SPP_ENABLED 1" in result.stdout
assert (build / "firmware.bin").stat().st_size > 0
assert list(build.glob("bt/**/btc_gap_bt.c.o"))
# No independent LDF-built BluetoothSerial may enter the linked program.
maps = list(build.glob("*.map"))
assert len(maps) == 1, maps
mapfile = maps[0].read_text()
assert "libBluetoothSerial.a" not in mapfile
component = original.parents[3].name
assert ("lib" + component + ".a(BluetoothSerial.cpp.o)") in mapfile, component
# Check the real codemodel target and its source, not a prefix lookalike.
reply = build / '.cmake/api/v1/reply'
model_files = list(reply.glob('codemodel-v2*.json'))
assert len(model_files) == 1
model = json.loads(model_files[0].read_text())
targets = model['configurations'][0]['targets']
matched = [t for t in targets if t['name'] == '__idf_' + component]
assert len(matched) == 1, component
target = json.loads((reply / matched[0]['jsonFile']).read_text())
assert any((Path(model['paths']['source']) / s['path']).resolve() == bt[0]
           for s in target['sources'])
print("PASS: SDK compiled without SSP; authenticated/encrypted SPP adaptation; no duplicate upstream library; mutable four-digit PIN policy; drift rejected; firmware produced")
