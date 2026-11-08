"""Build-local adaptation of pinned Arduino 2.0.17; never edit package sources."""
import pathlib
import sys


def adapt(text):
    def replace(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError(f"Arduino BluetoothSerial source changed: {old[:70]!r}")
        text = text.replace(old, new)

    replace('esp_spp_start_srv(ESP_SPP_SEC_NONE, ESP_SPP_ROLE_SLAVE, 0, _spp_server_name);',
            'if (param->init.status != ESP_SPP_SUCCESS ||\n'
            '                esp_spp_start_srv(ESP_SPP_SEC_AUTHENTICATE | ESP_SPP_SEC_ENCRYPT,\n'
            '                    ESP_SPP_ROLE_SLAVE, 0, _spp_server_name) != ESP_OK) {\n'
            '                log_e("Secure SPP server failed");\n'
            '            }')
    replace('        xEventGroupSetBits(_spp_event_group, SPP_RUNNING);\n        break;',
            '        break;')
    replace('    case ESP_SPP_START_EVT://server started\n        log_i("ESP_SPP_START_EVT");',
            '    case ESP_SPP_START_EVT://server started\n'
            '        if (param->start.status == ESP_SPP_SUCCESS) {\n'
            '            xEventGroupSetBits(_spp_event_group, SPP_RUNNING);\n'
            '        }')
    start = text.index('            // default pairing pins')
    end = text.index('        case ESP_BT_GAP_CONFIG_EIR_DATA_EVT:', start)
    replace(text[start:end],
            '            // Reject incompatible 16-digit requests; never use a fallback PIN.\n'
            '            esp_bt_gap_pin_reply(param->pin_req.bda,\n'
            '                _pin_len == 4 && !param->pin_req.min_16_digit,\n'
            '                _pin_len, _pin_code);\n'
            '            break;\n\n')
    start = text.index('    if (_isPinSet) {\n        log_i("pin set");')
    end = text.index('    // the default BTA_DM_COD', start)
    replace(text[start:end], '')
    replace('    if (esp_spp_init(ESP_SPP_MODE_CB) != ESP_OK){',
            '    // Configure the fixed legacy PIN before publishing any SPP service.\n'
            '    if (!_isPinSet || _pin_len != 4 || !btSetPin()) return false;\n\n'
            '    if (esp_spp_init(ESP_SPP_MODE_CB) != ESP_OK){')
    replace('    return _init_bt(local_name.c_str());',
            '    return _init_bt(local_name.c_str()) && isReady(false, READY_TIMEOUT);')
    replace('    log_i("pin: %s", pin);',
            '    if (!pin || strlen(pin) != 4) return false;\n'
            '    for (int i = 0; i < 4; ++i) if (pin[i] < \'0\' || pin[i] > \'9\') return false;' )
    replace('    if (isReady(false, READY_TIMEOUT)) {\n        btSetPin();\n    }',
            '    if (btStarted()) return btSetPin();')
    return ('// Generated locally from the pinned LGPL Arduino source; see original license below.\n'
            '#include "sdkconfig.h"\n'
            '#if defined(CONFIG_BT_SSP_ENABLED) || !defined(CONFIG_BT_SPP_ENABLED)\n'
            '#error RCDEV requires rebuilt Classic SPP with SSP disabled\n'
            '#endif\n' + text)


if __name__ == '__main__':
    source, destination = map(pathlib.Path, sys.argv[1:])
    destination.write_text(adapt(source.read_text()))
