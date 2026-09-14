"""CLI entrypoint: python -m umb_assistant"""

from umb_assistant.agent.chatbot import AdvisingAgent


def main():
    agent = AdvisingAgent()
    print("UMB Course Advising Assistant")
    print("Type your question below (Ctrl+C to quit).\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not question:
            continue
        reply = agent.send_message(question)
        print(f"\nAssistant: {reply}\n")


if __name__ == "__main__":
    main()

