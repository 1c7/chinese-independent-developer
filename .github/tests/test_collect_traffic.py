import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('collector', Path(__file__).parents[1] / 'scripts/collect_traffic.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def payload(metric, count=10):
    return {'count': count, 'uniques': 4, metric: [
        {'timestamp': '2026-10-13T00:00:00Z', 'count': count, 'uniques': 4}]}


class TrafficTests(unittest.TestCase):
    def test_overlap_replaces_counts_and_keeps_older_history(self):
        previous = [{'date': '2026-08-01', 'views': 99}, {'date': '2026-10-13', 'views': 5}]
        merged = collector.merge_daily(previous, payload('views'), payload('clones', 6))
        self.assertEqual(merged[0], previous[0])
        self.assertEqual(merged[1]['views'], 10)
        self.assertEqual(merged[1]['clones'], 6)
        self.assertEqual(len(merged), 2)
        self.assertEqual(collector.merge_daily(merged, payload('views'), payload('clones', 6)), merged)

    def test_manual_reruns_keep_history_and_one_snapshot_per_day(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            for _ in range(2):
                with patch.object(collector, 'fetch', side_effect=[payload('views'), payload('clones'), [], []]):
                    collector.collect('owner/repo', output, 'test-token')
            self.assertEqual(len(json.loads((output / 'daily.json').read_text())), 1)
            self.assertEqual(len(list((output / 'snapshots').glob('*.json'))), 1)
            self.assertNotIn('test-token', (output / 'latest.json').read_text())

    def test_endpoint_failure_does_not_overwrite_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            original = '[{"date": "2026-08-01", "views": 42}]'
            (output / 'daily.json').write_text(original)
            with patch.object(collector, 'fetch', side_effect=[payload('views'), RuntimeError('HTTP 403')]):
                with self.assertRaises(RuntimeError):
                    collector.collect('owner/repo', output, 'test-token')
            self.assertEqual((output / 'daily.json').read_text(), original)
            self.assertFalse((output / 'latest.json').exists())


if __name__ == '__main__':
    unittest.main()
