"""
Tests for Telegram power commands.
Run: cd E:/VSCode/Aisha && python scripts/test_telegram_commands.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

def _read_bot():
    with open("src/telegram/bot.py", encoding="utf-8") as f:
        return f.read()


def test_upload_command_exists():
    """Verify /upload handler is registered in bot.py."""
    content = _read_bot()
    assert 'commands=["upload"]' in content or "commands=['upload']" in content, \
        "/upload command not found in bot.py"
    print("✅ /upload command exists")


def test_queue_command_exists():
    content = _read_bot()
    assert 'commands=["queue"]' in content or "commands=['queue']" in content, \
        "/queue command not found"
    print("✅ /queue command exists")


def test_logs_command_exists():
    content = _read_bot()
    assert '"logs"' in content, "/logs command not found"
    print("✅ /logs command exists")


def test_shell_command_exists():
    content = _read_bot()
    assert '"shell"' in content, "/shell command not found"
    print("✅ /shell command exists")


def test_shell_confirmation_callback_exists():
    content = _read_bot()
    assert "shell_confirm_" in content, "Shell confirmation callback not found"
    print("✅ Shell confirmation callback exists")


def test_read_command_exists():
    content = _read_bot()
    assert '"read"' in content or 'commands=["read"]' in content, "/read command not found"
    print("✅ /read command exists")


def test_gitpull_command_exists():
    content = _read_bot()
    assert '"gitpull"' in content, "/gitpull command not found"
    print("✅ /gitpull command exists")


def test_restart_command_exists():
    content = _read_bot()
    assert '"restart"' in content, "/restart command not found"
    print("✅ /restart command exists")


def test_syscheck_command_exists():
    content = _read_bot()
    assert '"syscheck"' in content, "/syscheck command not found"
    print("✅ /syscheck command exists")


if __name__ == "__main__":
    tests = [
        test_upload_command_exists,
        test_queue_command_exists,
        test_logs_command_exists,
        test_shell_command_exists,
        test_shell_confirmation_callback_exists,
        test_read_command_exists,
        test_gitpull_command_exists,
        test_restart_command_exists,
        test_syscheck_command_exists,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} ERROR: {e}")
            failed += 1
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{passed+failed} passed")
    if failed > 0:
        sys.exit(1)
