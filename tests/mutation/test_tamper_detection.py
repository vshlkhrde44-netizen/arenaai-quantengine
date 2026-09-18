import json
from pathlib import Path
from core.marketdata.tamper_chain import TamperEvidentRawWriter, verify_tamper_chain


def create_base_chain(path: Path) -> Path:
    writer = TamperEvidentRawWriter("mutation_base", output_dir=path)
    writer.append_raw_message({"t": 1, "p": 100}, "trades", "BTC-USD", "coinbase")
    writer.append_raw_message({"t": 2, "p": 101}, "trades", "BTC-USD", "coinbase")
    writer.append_raw_message({"t": 3, "p": 102}, "trades", "BTC-USD", "coinbase")
    writer.append_raw_message({"t": 4, "p": 103}, "trades", "BTC-USD", "coinbase")
    writer.close()
    return writer.file_path


def test_mutation_deleted_record(tmp_path):
    orig = create_base_chain(tmp_path)
    lines = orig.read_text().splitlines()
    
    # Delete line 2 (seq 2)
    mutated = [lines[0], lines[2], lines[3]]
    mut_file = tmp_path / "deleted.jsonl"
    mut_file.write_text("\n".join(mutated) + "\n")

    valid, count, err = verify_tamper_chain(mut_file)
    assert valid is False
    assert "Sequence discontinuity" in err or "Hash chain break" in err


def test_mutation_reordered_records(tmp_path):
    orig = create_base_chain(tmp_path)
    lines = orig.read_text().splitlines()
    
    # Swap lines 1 and 2
    mutated = [lines[1], lines[0], lines[2], lines[3]]
    mut_file = tmp_path / "reordered.jsonl"
    mut_file.write_text("\n".join(mutated) + "\n")

    valid, count, err = verify_tamper_chain(mut_file)
    assert valid is False


def test_mutation_corrupted_json(tmp_path):
    orig = create_base_chain(tmp_path)
    lines = orig.read_text().splitlines()
    
    lines[2] = lines[2][:20] # Truncated broken JSON
    mut_file = tmp_path / "corrupt.jsonl"
    mut_file.write_text("\n".join(lines) + "\n")

    valid, count, err = verify_tamper_chain(mut_file)
    assert valid is False
    assert "Malformed JSON" in err
