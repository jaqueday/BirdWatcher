import os
import re
import sys
from collections import OrderedDict

# Ensure the project root is on the import path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from detection_stats import DetectionStats


def test_recent_activity_order(capsys):
    """ensure recent activity is reported in reverse chronological order"""
    stats = DetectionStats()

    # mock hourly breakdown to simulate crossing midnight
    stats.get_hourly_breakdown = lambda hours: OrderedDict([
        ('02:00', {'person': 1, 'dog': 0, 'bird': 0}),
        ('01:00', {'person': 1, 'dog': 0, 'bird': 0}),
        ('00:00', {'person': 1, 'dog': 0, 'bird': 0}),
        ('23:00', {'person': 1, 'dog': 0, 'bird': 0}),
        ('22:00', {'person': 1, 'dog': 0, 'bird': 0}),
        ('21:00', {'person': 1, 'dog': 0, 'bird': 0}),
    ])

    stats.print_summary()
    out = capsys.readouterr().out
    recent_hours = re.findall(r'^\s*(\d{2}:00):', out, flags=re.MULTILINE)

    assert recent_hours[:6] == ['02:00', '01:00', '00:00', '23:00', '22:00', '21:00']


