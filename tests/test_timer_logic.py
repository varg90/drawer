import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.timer_logic import validate_timer_seconds, format_time, auto_warn_seconds

def test_validate_timer_valid():
    assert validate_timer_seconds(1) == 1
    assert validate_timer_seconds(60) == 60
    assert validate_timer_seconds(10800) == 10800

def test_validate_timer_clamps_low():
    assert validate_timer_seconds(0) == 1
    assert validate_timer_seconds(-5) == 1

def test_validate_timer_clamps_high():
    assert validate_timer_seconds(10801) == 10800
    assert validate_timer_seconds(99999) == 10800

def test_validate_timer_float():
    assert validate_timer_seconds(5.7) == 5

def test_validate_timer_boundary():
    assert validate_timer_seconds(1) == 1
    assert validate_timer_seconds(10800) == 10800

def test_format_time_seconds():
    assert format_time(0) == "0:00"
    assert format_time(1) == "0:01"
    assert format_time(59) == "0:59"

def test_format_time_minutes():
    assert format_time(60) == "1:00"
    assert format_time(90) == "1:30"
    assert format_time(3599) == "59:59"

def test_format_time_hours():
    assert format_time(3600) == "1:00:00"
    assert format_time(3661) == "1:01:01"
    assert format_time(10800) == "3:00:00"

def test_auto_warn_up_to_2min():
    assert auto_warn_seconds(1) == 10
    assert auto_warn_seconds(120) == 10

def test_auto_warn_2min_to_5min():
    assert auto_warn_seconds(121) == 30
    assert auto_warn_seconds(300) == 30

def test_auto_warn_5min_to_15min():
    assert auto_warn_seconds(301) == 60
    assert auto_warn_seconds(900) == 60

def test_auto_warn_15min_to_1hour():
    assert auto_warn_seconds(901) == 300
    assert auto_warn_seconds(3600) == 300

def test_auto_warn_1hour_to_3hours():
    assert auto_warn_seconds(3601) == 600
    assert auto_warn_seconds(10800) == 600

def test_auto_warn_boundaries():
    assert auto_warn_seconds(120) == 10
    assert auto_warn_seconds(121) == 30
    assert auto_warn_seconds(300) == 30
    assert auto_warn_seconds(301) == 60
    assert auto_warn_seconds(900) == 60
    assert auto_warn_seconds(901) == 300
    assert auto_warn_seconds(3600) == 300
    assert auto_warn_seconds(3601) == 600
