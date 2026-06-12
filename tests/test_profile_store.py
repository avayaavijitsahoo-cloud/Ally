from backend.profile_store import get_profile_summary, save_facts


def test_save_facts_deduplicates_and_summarizes(tmp_path, monkeypatch):
    import backend.database as database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    save_facts([
        {"category": "history", "content": "Name is Reva"},
        {"category": "history", "content": "Name is Reva"},
    ])

    summary = get_profile_summary()

    assert summary.count("Name is Reva") == 1
