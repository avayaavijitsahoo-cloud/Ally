from backend.prompt_builder import build_conversation_messages


def test_build_conversation_messages_appends_user_message():
    messages = build_conversation_messages(
        [{"role": "assistant", "content": "Hi"}],
        "My name is Reva",
    )

    assert messages[-1] == {"role": "user", "content": "My name is Reva"}
