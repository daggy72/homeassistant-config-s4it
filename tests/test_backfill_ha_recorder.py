import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "telemetry" / "backfill-ha-recorder.py"
SPEC = importlib.util.spec_from_file_location("backfill_ha_recorder", MODULE_PATH)
backfill = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = backfill
SPEC.loader.exec_module(backfill)


class BackfillHelpersTest(unittest.TestCase):
    def test_line_protocol_escapes_measurement_tags_and_fields(self):
        line = backfill.line_protocol(
            "°C",
            {"entity_id": "wh1 temperature", "friendly_name": "WH1, S1"},
            {"value": 18.5, "note": 'sensor "moved"'},
            1779870000.9,
        )

        self.assertEqual(
            line,
            '°C,entity_id=wh1\\ temperature,friendly_name=WH1\\,\\ S1 value=18.5,note="sensor \\"moved\\"" 1779870000',
        )

    def test_state_fields_convert_numeric_and_boolean_states(self):
        self.assertEqual(backfill.state_fields("18.5", {}), {"value": 18.5})
        self.assertEqual(backfill.state_fields("on", {}), {"value": 1.0, "state": "on"})
        self.assertEqual(backfill.state_fields("off", {}), {"value": 0.0, "state": "off"})
        self.assertEqual(backfill.state_fields("unavailable", {}), {})

    def test_state_fields_keep_allowed_numeric_attributes(self):
        fields = backfill.state_fields(
            "cool",
            {"current_temperature": 24.2, "valve_open_percent": "35", "supported_features": 401},
        )

        self.assertEqual(
            fields,
            {"state": "cool", "current_temperature": 24.2, "valve_open_percent": 35.0},
        )

    def test_parse_include_config_reads_entities_and_globs(self):
        path = Path("/tmp/backfill-influxdb-test.yaml")
        path.write_text(
            "\n".join(
                [
                    "include:",
                    "  entities:",
                    "    - sensor.wh1_temperature",
                    "  entity_globs:",
                    "    - sensor.*temperature*",
                ]
            )
        )

        include = backfill.parse_include_config(path)

        self.assertTrue(include.matches("sensor.wh1_temperature"))
        self.assertTrue(include.matches("sensor.reception_temperature"))
        self.assertFalse(include.matches("sensor.random_humidity"))

    def test_quality_lines_mark_start_and_end_without_changing_raw_data(self):
        lines = backfill.quality_lines(
            "2026-05-24T00:00:00+02:00",
            "2026-05-27T10:45:00+02:00",
        )

        self.assertEqual(len(lines), 2)
        self.assertIn("telemetry_quality", lines[0])
        self.assertIn("value=1i", lines[0])
        self.assertIn("value=0i", lines[1])


if __name__ == "__main__":
    unittest.main()
