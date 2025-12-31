from api import utils


def test_generate_request_id_format():
    request_id = utils.generate_request_id()
    assert isinstance(request_id, str)
    assert len(request_id) > 0


def test_sanitize_log_data():
    data = {"api_key": "123456", "token": "tok", "other": "v"}
    sanitized = utils.sanitize_log_data(data)
    assert sanitized["api_key"] == "***REDACTED***"
    assert sanitized["token"] == "***REDACTED***"
    assert sanitized["other"] == "v"


def test_request_logger_logs(monkeypatch, capsys):
    logger = utils.logging.getLogger("testlogger")
    rl = utils.RequestLogger(request_id="rid", logger=logger)

    # reemplazar los métodos del logger para capturar la salida en stdout
    def fake_info(msg):
        print(msg)

    monkeypatch.setattr(logger, "info", fake_info)
    rl.info("hello", extra=1)
    captured = capsys.readouterr()
    assert "rid" in captured.out
    assert "hello" in captured.out
