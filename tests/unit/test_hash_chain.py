import json
from pathlib import Path
from core.marketdata.tamper_chain import TamperEvidentRawWriter, verify_tamper_chain, GENESIS_HASH


def test_tamper_chain_creation_and_verification(tmp_path):
    writer = TamperEvidentRawWriter("session_test_unit", output_dir=tmp_path)
    
    msg1 = {"trade_id": "t1", "price": 100.0, "qty": 1.0}
    msg2 = {"trade_id": "t2", "price": 101.5, "qty": 0.5}
    msg3 = {"trade_id": "t3", "price": 99.8, "qty": 2.0}

    writer.append_raw_message(msg1, "trades", "BTC-USD", "coinbase")
    writer.append_raw_message(msg2, "trades", "BTC-USD", "coinbase")
    writer.append_raw_message(msg3, "trades", "BTC-USD", "coinbase")
    writer.close()

    valid, count, err = verify_tamper_chain(writer.file_path)
    assert valid is True
    assert count == 3
    assert err is None


def test_tamper_detection_on_payload_modification(tmp_path):
    writer = TamperEvidentRawWriter("session_tamper_mod", output_dir=tmp_path)
    writer.append_raw_message({"price": 50.0}, "ticker", "ETH-USD", "coinbase")
    writer.append_raw_message({"price": 52.0}, "ticker", "ETH-USD", "coinbase")
    writer.close()

    # Tamper with file
    lines = writer.file_path.read_text().splitlines()
    rec2 = json.loads(lines[1])
    rec2["raw_payload"] = '{"price":9999.0}' # Injected altered price
    lines[1] = json.dumps(rec2)
    writer.file_path.write_text("\n".join(lines) + "\n")

    valid, count, err = verify_tamper_chain(writer.file_path)
    assert valid is False
    assert "Tampered record" in err
