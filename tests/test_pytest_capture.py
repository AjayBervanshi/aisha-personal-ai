def test_capture(capsys):
    print("hello from pytest capture")
    captured = capsys.readouterr()
    assert "hello from pytest capture" in captured.out
