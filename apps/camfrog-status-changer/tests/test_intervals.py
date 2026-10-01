from automation.intervals import interval_to_seconds

def test_units():
    assert interval_to_seconds(30,"seconds")==30
    assert interval_to_seconds(2,"minutes")==120
    assert interval_to_seconds(1,"hours")==3600
