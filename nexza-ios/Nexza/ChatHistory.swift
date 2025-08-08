import Foundation

/// `ChatHistory` manages an array of `ChatMessage` objects and persists
/// them to a local JSON file in the user's documents directory. Every
/// time the `messages` array is modified the history is saved to disk.
class ChatHistory: ObservableObject {
    /// The list of messages in chronological order. Updating this
    /// property triggers a save to disk via the `didSet` observer.
    @Published var messages: [ChatMessage] = [] {
        didSet {
            save()
        }
    }

    /// The location on disk where chat history is stored. The file is
    /// stored under the documents directory as `chat_history.json`.
    private let fileURL: URL = {
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return dir.appendingPathComponent("chat_history.json")
    }()

    init() {
        load()
    }

    /// Loads existing chat history from disk. If no file exists or the
    /// contents cannot be decoded, the messages array remains empty.
    private func load() {
        guard let data = try? Data(contentsOf: fileURL) else { return }
        if let decoded = try? JSONDecoder().decode([ChatMessage].self, from: data) {
            messages = decoded
        }
    }

    /// Saves the current messages array to disk as JSON. Errors are
    /// intentionally ignored to avoid crashing the app on save failure.
    private func save() {
        if let data = try? JSONEncoder().encode(messages) {
            try? data.write(to: fileURL)
        }
    }

    /// Appends a new message to the history.
    func addMessage(_ message: ChatMessage) {
        messages.append(message)
    }

    /// Clears the history by removing all messages.
    func clear() {
        messages.removeAll()
    }
}